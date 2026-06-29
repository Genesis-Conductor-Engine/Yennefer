#!/usr/bin/env bash
# MARU MCP Runtime Launch Script
# Envelope Version: 0.3.0
# Hardware: GTX 1650 4GB VRAM substrate
# Partitioning: JAX 45% | CUDA-Q 55% | Interleaved Bus

set -euo pipefail

readonly ENVELOPE_VERSION="0.3.0"
readonly CONTAINER_NAME="maru-runtime"
readonly IMAGE="nvidia/cuda:12.8.0-runtime-ubuntu22.04"
readonly APP_PORT=8000
readonly METRICS_PORT=9090

# VRAM Partitioning Constants
readonly JAX_VRAM_FRACTION=0.45
readonly CUDA_Q_VRAM_FRACTION=0.55
readonly GPU_DEVICE=0

# Paths
readonly PROJECT_ROOT="${HOME}/diamondnode-unified-inference"
readonly SRC_DIR="${PROJECT_ROOT}/src"
readonly CONFIG_DIR="${PROJECT_ROOT}/config"
readonly DEPLOYMENT_DIR="${PROJECT_ROOT}/deployment"
readonly MARU_STATE_DIR="/var/lib/maru_state"

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

log() { echo -e "${GREEN}[MARU]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*" >&2; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

check_prerequisites() {
    log "Checking prerequisites (envelope: ${ENVELOPE_VERSION})..."
    
    command -v podman >/dev/null 2>&1 || error "podman not found"
    command -v nvidia-smi >/dev/null 2>&1 || error "nvidia-smi not found"
    
    [[ -d "${SRC_DIR}" ]] || error "Source directory not found: ${SRC_DIR}"
    [[ -d "${CONFIG_DIR}" ]] || error "Config directory not found: ${CONFIG_DIR}"
    
    local vram_mb
    vram_mb=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
    if [[ ${vram_mb} -lt 4000 ]]; then
        error "Insufficient VRAM: ${vram_mb}MB (expected ~4096MB)"
    fi
    
    log "✓ Prerequisites validated"
}

setup_maru_state() {
    log "Setting up MARU state directory..."
    
    sudo mkdir -p "${MARU_STATE_DIR}"
    sudo chown "${USER}:${USER}" "${MARU_STATE_DIR}"
    chmod 755 "${MARU_STATE_DIR}"
    
    if [[ ! -f "${MARU_STATE_DIR}/nox_state.json" ]]; then
        cp "${DEPLOYMENT_DIR}/nox_engine_state.json" "${MARU_STATE_DIR}/nox_state.json"
        log "✓ Initialized NOX engine state"
    fi
    
    touch "${MARU_STATE_DIR}/bus_state.log"
    touch "${MARU_STATE_DIR}/vram_violations.log"
    
    log "✓ MARU state directory ready: ${MARU_STATE_DIR}"
}

stop_existing_container() {
    if podman ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log "Stopping existing container..."
        podman stop "${CONTAINER_NAME}" 2>/dev/null || true
        podman rm "${CONTAINER_NAME}" 2>/dev/null || true
    fi
}

launch_container() {
    log "Launching MARU runtime container..."
    log "  JAX VRAM: ${JAX_VRAM_FRACTION} (45%)"
    log "  CUDA-Q VRAM: ${CUDA_Q_VRAM_FRACTION} (55%)"
    log "  Interleaved Bus: ENABLED"
    log "  Guardian Mode: ENABLED"
    
    podman run -d \
        --name "${CONTAINER_NAME}" \
        --hostname maru-runtime \
        \
        --device nvidia.com/gpu=all \
        --security-opt=label=disable \
        \
        --memory=14g \
        --memory-swap=16g \
        --cpus=6 \
        \
        -e XLA_PYTHON_CLIENT_MEM_FRACTION="${JAX_VRAM_FRACTION}" \
        -e CUDA_VISIBLE_DEVICES="${GPU_DEVICE}" \
        -e MARU_GUARDIAN_MODE=enabled \
        -e NOX_ENGINE_STATE=/var/maru/nox_state.json \
        -e CUDA_Q_LANES=4 \
        -e INTERLEAVED_BUS=true \
        -e ENVELOPE_VERSION="${ENVELOPE_VERSION}" \
        -e JAX_VRAM_CEILING_MB=1800 \
        -e CUDA_Q_VRAM_CEILING_MB=2200 \
        -e PYTHONUNBUFFERED=1 \
        \
        -v "${SRC_DIR}:/app/src:ro" \
        -v "${CONFIG_DIR}:/app/config:ro" \
        -v "${MARU_STATE_DIR}:/var/maru:rw" \
        \
        -p "${APP_PORT}:8000" \
        -p "${METRICS_PORT}:9090" \
        \
        --restart=unless-stopped \
        \
        --health-cmd="curl -f http://localhost:8000/health || exit 1" \
        --health-interval=30s \
        --health-timeout=10s \
        --health-retries=3 \
        --health-start-period=40s \
        \
        "${IMAGE}" \
        bash -c "
            apt-get update -qq && apt-get install -y -qq python3 python3-pip curl >/dev/null 2>&1 &&
            pip3 install --quiet fastapi uvicorn jax[cuda12] numpy pynvml &&
            cd /app &&
            python3 /var/maru/interleaved_bus_monitor.py &
            python3 /var/maru/vram_guardian.py &
            exec uvicorn src.main:app --host 0.0.0.0 --port 8000
        "
    
    log "✓ Container launched: ${CONTAINER_NAME}"
}

wait_for_health() {
    log "Waiting for health check..."
    local max_attempts=30
    local attempt=0
    
    while [[ ${attempt} -lt ${max_attempts} ]]; do
        if curl -sf "http://localhost:${APP_PORT}/health" >/dev/null 2>&1; then
            log "✓ Service healthy"
            return 0
        fi
        ((attempt++))
        sleep 2
    done
    
    error "Health check failed after ${max_attempts} attempts"
}

display_status() {
    log "═══════════════════════════════════════════════════"
    log "MARU MCP Runtime - ACTIVE"
    log "═══════════════════════════════════════════════════"
    log "Envelope Version: ${ENVELOPE_VERSION}"
    log "Container: ${CONTAINER_NAME}"
    log "GPU: GTX 1650 4GB VRAM"
    log ""
    log "VRAM Partitioning:"
    log "  ├─ JAX/hyperNEAT:  45% (1800MB ceiling)"
    log "  ├─ CUDA-Q lanes:   55% (2200MB ceiling)"
    log "  └─ Interleaved:    ENABLED"
    log ""
    log "Endpoints:"
    log "  ├─ Application:    http://localhost:${APP_PORT}"
    log "  ├─ Health:         http://localhost:${APP_PORT}/health"
    log "  └─ Metrics:        http://localhost:${METRICS_PORT}/metrics"
    log ""
    log "State Files:"
    log "  ├─ NOX Engine:     ${MARU_STATE_DIR}/nox_state.json"
    log "  ├─ Bus Log:        ${MARU_STATE_DIR}/bus_state.log"
    log "  └─ VRAM Log:       ${MARU_STATE_DIR}/vram_violations.log"
    log ""
    log "Commands:"
    log "  ├─ Logs:           podman logs -f ${CONTAINER_NAME}"
    log "  ├─ Stats:          podman stats ${CONTAINER_NAME}"
    log "  ├─ Stop:           podman stop ${CONTAINER_NAME}"
    log "  └─ Shell:          podman exec -it ${CONTAINER_NAME} bash"
    log "═══════════════════════════════════════════════════"
}

main() {
    log "MARU MCP Runtime Launch (envelope: ${ENVELOPE_VERSION})"
    
    check_prerequisites
    setup_maru_state
    stop_existing_container
    launch_container
    wait_for_health
    display_status
    
    log "✅ MARU runtime operational - Zero OOM tolerance enforced"
}

main "$@"
