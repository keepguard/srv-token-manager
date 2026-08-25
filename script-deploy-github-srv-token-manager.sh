#!/bin/bash

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVICE_NAME="srv-token-manager"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/config/application.yaml"
DOCKER_COMPOSE_FILE="${PROJECT_ROOT}/docker/docker-compose.yml"

# Funções de log
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Função para extrair versão do config
get_current_version() {
    grep 'version:' "$CONFIG_FILE" | sed 's/.*version: *"\(.*\)".*/\1/' | tr -d ' 	'
}

# Função para incrementar versão
increment_version() {
    local version=$1
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)
    local patch=$(echo $version | cut -d. -f3)
    
    patch=$((patch + 1))
    echo "${major}.${minor}.${patch}"
}

# Função para atualizar versão no config
update_config_version() {
    local new_version=$1
    log_info "Atualizando config para versão: $new_version"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|version: \".*\"|version: \"$new_version\"|g" "$CONFIG_FILE"
    else
        sed -i "s|version: \".*\"|version: \"$new_version\"|g" "$CONFIG_FILE"
    fi
    
    log_success "Config atualizado para: $new_version"
}

# Verificar parâmetros
DEPLOY_DOCKER=false
if [ "$1" = "up" ]; then
    DEPLOY_DOCKER=true
    log_info "Modo: Build + Push + Deploy Docker"
else
    log_info "Modo: Build + Push (GitHub apenas)"
fi

# Extrai versão do config

# Commita e faz push das alterações do repositório do serviço após o release
commit_and_push_release() {
    local release_version=$1
    local repo_dir=${2:-"${SCRIPT_DIR}"}

    log_step "Commit e push das alterações (Release ${release_version})..."

    if ! git -C "${repo_dir}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        log_warning "Diretório não é um repositório git: ${repo_dir}. Pulando commit/push."
        return 0
    fi

    pushd "${repo_dir}" > /dev/null

    git add -A
    if git diff --cached --quiet; then
        log_info "Nenhuma alteração pendente para commit."
        popd > /dev/null
        return 0
    fi

    if ! git commit -m "$(cat <<EOF
Release ${release_version}

EOF
)"; then
        log_error "Falha ao criar commit do release ${release_version}"
        popd > /dev/null
        return 1
    fi

    if ! git push; then
        log_error "Falha ao fazer push do release ${release_version}"
        popd > /dev/null
        return 1
    fi

    log_success "Commit e push concluídos (Release ${release_version})"
    popd > /dev/null
    return 0
}


VERSION=$(get_current_version)

if [ -z "$VERSION" ]; then
    log_error "Não foi possível extrair a versão do config"
    exit 1
fi

log_info "Versão detectada: ${VERSION}"

# Define imagens
REGISTRY="ghcr.io/keepguard"
IMAGE_NAME="${REGISTRY}/${SERVICE_NAME}"
IMAGE_TAG="${IMAGE_NAME}:${VERSION}"
IMAGE_LATEST="${IMAGE_NAME}:latest"

log_info "============================================"
log_info "  Deploy ${SERVICE_NAME}"
log_info "============================================"
log_info "Registry: ${REGISTRY}"
log_info "Image: ${IMAGE_TAG}"
log_info "============================================"

# 1. Build Docker Image
log_info "Construindo imagem Docker..."
docker build -t "${IMAGE_TAG}" -t "${IMAGE_LATEST}" .

if [ $? -ne 0 ]; then
    log_error "Falha ao construir imagem Docker"
    exit 1
fi

log_success "Imagem Docker construída: ${IMAGE_TAG}"

# 2. Push para GitHub Container Registry
log_info "Fazendo push para GitHub Container Registry..."
docker push "${IMAGE_TAG}"
docker push "${IMAGE_LATEST}"

if [ $? -ne 0 ]; then
    log_error "Falha ao fazer push da imagem"
    exit 1
fi

log_success "Push concluído com sucesso"

# 3. Atualiza docker-compose.yml
log_info "Atualizando docker-compose.yml..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|image: ${REGISTRY}/${SERVICE_NAME}:.*|image: ${IMAGE_TAG}|g" "${DOCKER_COMPOSE_FILE}"
else
    sed -i "s|image: ${REGISTRY}/${SERVICE_NAME}:.*|image: ${IMAGE_TAG}|g" "${DOCKER_COMPOSE_FILE}"
fi
log_success "docker-compose.yml atualizado"

    # 4. Deploy no Docker Compose (se parâmetro "up")
    if [ "$DEPLOY_DOCKER" = true ]; then
        log_info "Fazendo deploy no Docker Compose..."
        cd "${PROJECT_ROOT}/docker"
        docker compose pull ${SERVICE_NAME}
        docker compose up -d --force-recreate ${SERVICE_NAME}
        
        if [ $? -eq 0 ]; then
            log_success "Container ${SERVICE_NAME} iniciado com sucesso"
            
            # Aguardar health check
            log_info "Aguardando health check..."
            sleep 10
            
            HEALTH_URL="http://localhost:8700/health"
            if curl -s ${HEALTH_URL} | grep -q "UP"; then
                log_success "Serviço está saudável!"
            else
                log_warning "Verificar logs: docker logs srv-token-manager"
            fi
        else
            log_warning "Falha ao iniciar container ${SERVICE_NAME}"
        fi
        
        cd - > /dev/null
    fi

# 5. Auto-incrementa versão no config
log_info "Incrementando versão no config..."
NEXT_VERSION=$(increment_version "$VERSION")
update_config_version "$NEXT_VERSION"

commit_and_push_release "${VERSION}" "${SCRIPT_DIR}"

log_success "============================================"
log_success "  Deploy concluído com sucesso!"
log_success "============================================"
log_info "Imagem: ${IMAGE_TAG}"
log_info "Latest: ${IMAGE_LATEST}"
log_info "Próxima versão: ${NEXT_VERSION}"
log_success "============================================"
