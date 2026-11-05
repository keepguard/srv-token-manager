#!/bin/bash
# =============================================================================
# 🚀 MINI MANUAL DE USO — script-deploy-github-srv-token-manager.sh
# =============================================================================
#
#   1. Apenas commit e push na branch atual (ex: develop):
#      $ ./script-deploy-github-srv-token-manager.sh
#
#   2. Commit, push na branch atual + Merge para 'main':
#      $ ./script-deploy-github-srv-token-manager.sh merge main
#
#   3. PRODUÇÃO (Commit + Push + Merge para 'main' + Deploy K8s via GitHub Actions):
#      $ ./script-deploy-github-srv-token-manager.sh prod
#
#   4. Opcional: Subir container no Docker Compose local:
#      $ ./script-deploy-github-srv-token-manager.sh up
#
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="srv-token-manager"
DOCKER_COMPOSE_DIR="${SCRIPT_DIR}/../../../docker"
DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_DIR}/docker-compose.yml"
REGISTRY="ghcr.io/keepguard"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

MERGE_TARGET=""
DEPLOY_DOCKER=false
TRIGGER_PROD=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        up)
            DEPLOY_DOCKER=true
            shift
            ;;
        prod)
            MERGE_TARGET="main"
            TRIGGER_PROD=true
            shift
            ;;
        merge)
            MERGE_TARGET="${2:-main}"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

cd "${SCRIPT_DIR}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    log_error "Diretório não é um repositório git."
    exit 1
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
log_step "1/3 Verificando repositório Git na branch '${CURRENT_BRANCH}'..."
git pull origin "${CURRENT_BRANCH}" --rebase || true
git add -A
if ! git diff --cached --quiet; then
    log_info "Criando commit com alterações pendentes..."
    git commit -m "feat(${SERVICE_NAME}): update ${SERVICE_NAME} $(date +'%Y-%m-%d %H:%M')"
    log_info "Fazendo push para branch '${CURRENT_BRANCH}'..."
    git push origin "${CURRENT_BRANCH}"
else
    log_info "Nenhuma alteração pendente na branch '${CURRENT_BRANCH}'."
    git push origin "${CURRENT_BRANCH}" || true
fi

LOCAL_SHA=$(git rev-parse --short HEAD)

if [ -n "$MERGE_TARGET" ] && [ "$MERGE_TARGET" != "$CURRENT_BRANCH" ]; then
    log_step "2/3 Promovendo branch '${CURRENT_BRANCH}' para '${MERGE_TARGET}'..."
    git checkout "${MERGE_TARGET}"
    git pull origin "${MERGE_TARGET}" --rebase || true
    git merge "${CURRENT_BRANCH}" -m "chore(merge): merge branch '${CURRENT_BRANCH}' into ${MERGE_TARGET}"
    git push origin "${MERGE_TARGET}"
    BUILD_SHA=$(git rev-parse --short HEAD)
    log_info "Retornando checkout com segurança para '${CURRENT_BRANCH}'..."
    git checkout "${CURRENT_BRANCH}"
else
    BUILD_SHA="${LOCAL_SHA}"
fi

echo
log_info "============================================"
log_info "  Status ${SERVICE_NAME}"
log_info "============================================"
log_info "Branch de Trabalho : ${CURRENT_BRANCH}"
log_info "Commit SHA         : ${BUILD_SHA}"
log_info "Deploy Produção    : ${TRIGGER_PROD}"
log_info "Deploy Local (up)  : ${DEPLOY_DOCKER}"
log_info "============================================"
echo

if [ "$DEPLOY_DOCKER" = true ]; then
    log_step "Construindo imagem localmente para o Docker Compose..."
    if command -v docker >/dev/null 2>&1; then
        if [ "$CURRENT_BRANCH" = "main" ]; then
            PRIMARY_TAG="${REGISTRY}/${SERVICE_NAME}:${BUILD_SHA}"
            LATEST_TAG="${REGISTRY}/${SERVICE_NAME}:latest"
        else
            PRIMARY_TAG="${REGISTRY}/${SERVICE_NAME}:${CURRENT_BRANCH}-${BUILD_SHA}"
            LATEST_TAG="${REGISTRY}/${SERVICE_NAME}:${CURRENT_BRANCH}-latest"
        fi
        DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -f Dockerfile -t "${PRIMARY_TAG}" -t "${LATEST_TAG}" .
        docker push "${PRIMARY_TAG}" || true
        docker push "${LATEST_TAG}" || true
        if [ -d "${DOCKER_COMPOSE_DIR}" ] && [ -f "${DOCKER_COMPOSE_FILE}" ]; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|image: ${REGISTRY}/${SERVICE_NAME}:.*|image: ${PRIMARY_TAG}|g" "${DOCKER_COMPOSE_FILE}"
            else
                sed -i "s|image: ${REGISTRY}/${SERVICE_NAME}:.*|image: ${PRIMARY_TAG}|g" "${DOCKER_COMPOSE_FILE}"
            fi
            log_info "docker-compose.yml atualizado para ${PRIMARY_TAG}"
            cd "${DOCKER_COMPOSE_DIR}"
            docker compose pull "${SERVICE_NAME}" || true
            docker compose up -d --no-deps --force-recreate "${SERVICE_NAME}" || true
            log_success "Container ${SERVICE_NAME} recriado localmente!"
        fi
    else
        log_warn "Docker não encontrado/ativo para subir localmente."
    fi
fi

if [ "$TRIGGER_PROD" = true ]; then
    log_step "3/3 Acompanhando build no GitHub Actions e aplicando Helm via SSH (porta 22)..."
    if command -v gh >/dev/null 2>&1; then
        RUN_ID=""
        for _ in $(seq 1 30); do
            RUN_ID=$(gh run list -R "keepguard/${SERVICE_NAME}" --branch main --limit 5 --json databaseId,headSha --jq ".[] | select(.headSha | startswith(\"${BUILD_SHA}\")) | .databaseId" | head -1)
            [ -n "${RUN_ID}" ] && break
            sleep 2
        done
        if [ -z "${RUN_ID}" ]; then
            log_error "Build de ${BUILD_SHA} não apareceu no GitHub Actions em 60 s: nada foi aplicado."
            exit 1
        fi
        if ! gh run watch "${RUN_ID}" -R "keepguard/${SERVICE_NAME}" --exit-status --interval 15; then
            log_error "O build de ${BUILD_SHA} FALHOU: nada foi aplicado."
            exit 1
        fi
    fi
    sed -i '' "s|^[[:space:]]*tag:.*|  tag: \"${BUILD_SHA}\"|g" "${SCRIPT_DIR}/helm/values.yaml"
    git add "${SCRIPT_DIR}/helm/values.yaml"
    if ! git diff --cached --quiet; then
        git commit -q -m "chore(helm): bump ${SERVICE_NAME} image tag to ${BUILD_SHA}"
        git push origin "${CURRENT_BRANCH}" || true
    fi
    # Deployment por replace (o chart é a verdade): o apply sobre Deployment criado sem a anotação do kubectl
    # mantinha variáveis que saíram do chart e misturava value com valueFrom (deploy inválido na janela de vhost,
    # 05/11/2026). Demais recursos seguem por apply. --save-config deixa a anotação para os próximos.
    HELM_TMP="$(mktemp -d)"
    helm template "${SERVICE_NAME}" "${SCRIPT_DIR}/helm" -n keepguard > "${HELM_TMP}/todos.yaml"
    python3 - "${HELM_TMP}" <<'PY_SEPARAR'
import sys, yaml
d = sys.argv[1]
docs = [x for x in yaml.safe_load_all(open(d + "/todos.yaml")) if x]
yaml.safe_dump_all([x for x in docs if x.get("kind") == "Deployment"], open(d + "/deployment.yaml", "w"))
yaml.safe_dump_all([x for x in docs if x.get("kind") != "Deployment"], open(d + "/resto.yaml", "w"))
PY_SEPARAR
    if grep -q "kind:" "${HELM_TMP}/resto.yaml"; then
        ssh -o BatchMode=yes root@31.97.175.92 "kubectl apply -n keepguard -f -" < "${HELM_TMP}/resto.yaml"
    fi
    ssh -o BatchMode=yes root@31.97.175.92 'T=$(mktemp) && cat > "$T" && { kubectl -n keepguard replace --save-config -f "$T" || kubectl -n keepguard create --save-config -f "$T"; }; R=$?; rm -f "$T"; exit $R' < "${HELM_TMP}/deployment.yaml"
    rm -rf "${HELM_TMP}"
    ssh -o BatchMode=yes root@31.97.175.92 "kubectl rollout status deployment/${SERVICE_NAME} -n keepguard --timeout=300s"
    if [ -x "${SCRIPT_DIR}/../../../scripts/verificar-infra.sh" ]; then
        "${SCRIPT_DIR}/../../../scripts/verificar-infra.sh"
    fi
fi

log_success "============================================"
log_success "  Operação concluída com sucesso!"
log_success "============================================"
