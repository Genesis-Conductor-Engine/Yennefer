#!/bin/bash
# Yennefer Native Deployment Script
# Deploys Yennefer services without Docker (for local development)
# Usage: bash deploy_yennefer_native.sh [start|stop|restart|status]

set -e

YENNEFER_ROOT="/home/diamondnode/Yennefer"
GENESIS_QMEM="$YENNEFER_ROOT/genesis-q-mem"
SCRIPTS_DIR="$YENNEFER_ROOT/scripts"
LOGS_DIR="$YENNEFER_ROOT/logs"
PIDS_DIR="$YENNEFER_ROOT/.pids"

# Ensure directories exist
mkdir -p "$LOGS_DIR" "$PIDS_DIR"

# Service definitions
SERVICES=(
  "diamond-vault:qmcp_admin_panel.py:8100:$GENESIS_QMEM"
  "soul-api:a2a_handoff_server.py:8088:$GENESIS_QMEM"
  "qmem-gateway:qmem_bubble_gateway_v2.py:8003:$GENESIS_QMEM"
  "qmcp-bridge:qmcp_blockchain_bridge.py::$GENESIS_QMEM"
  "process-guardian:process_guardian.cjs::$SCRIPTS_DIR"
  "conductor:conductor_node.cjs::$SCRIPTS_DIR"
  "qmcp-bridge-node:qmcp_genesis_bridge.cjs::$SCRIPTS_DIR"
)

# Health check endpoints
HEALTH_CHECKS=(
  "http://localhost:8100/health"
  "http://localhost:8088/api/soul"
  "http://localhost:8003/api/health"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log() {
  echo -e "${BLUE}[Yennefer]${NC} $1"
}

success() {
  echo -e "${GREEN}[Yennefer]${NC} $1"
}

warn() {
  echo -e "${YELLOW}[Yennefer]${NC} $1"
}

error() {
  echo -e "${RED}[Yennefer]${NC} $1"
}

# Check if service is running
is_running() {
  local service_name="$1"
  local pid_file="$PIDS_DIR/${service_name}.pid"
  
  if [ -f "$pid_file" ]; then
    local pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      return 0
    else
      rm -f "$pid_file"
      return 1
    fi
  fi
  return 1
}

# Start a single service
start_service() {
  local service_def="$1"
  local IFS=':'
  read -r -a parts <<< "$service_def"
  local service_name="${parts[0]}"
  local script_file="${parts[1]}"
  local port="${parts[2]}"
  local work_dir="${parts[3]}"
  
  local pid_file="$PIDS_DIR/${service_name}.pid"
  local log_file="$LOGS_DIR/${service_name}.log"
  
  if is_running "$service_name"; then
    log "Service $service_name is already running (PID: $(cat $pid_file))"
    return 0
  fi
  
  log "Starting $service_name..."
  cd "$work_dir"
  
  # Determine if it's Python or Node.js
  if [[ "$script_file" == *.py ]]; then
    nohup /home/diamondnode/venv312/bin/python "$script_file" > "$log_file" 2>&1 &
  elif [[ "$script_file" == *.cjs ]]; then
    nohup /home/diamondnode/.npm-global/bin/node "$script_file" > "$log_file" 2>&1 &
  else
    nohup "$script_file" > "$log_file" 2>&1 &
  fi
  
  local pid=$!
  echo "$pid" > "$pid_file"
  
  # Wait a bit for service to start
  sleep 2
  
  if is_running "$service_name"; then
    success "Service $service_name started (PID: $pid)"
    if [ -n "$port" ]; then
      success "  Accessible at: http://localhost:$port"
    fi
  else
    error "Failed to start $service_name"
    rm -f "$pid_file"
    return 1
  fi
}

# Stop a single service
stop_service() {
  local service_name="$1"
  local pid_file="$PIDS_DIR/${service_name}.pid"
  
  if ! is_running "$service_name"; then
    log "Service $service_name is not running"
    return 0
  fi
  
  local pid=$(cat "$pid_file")
  log "Stopping $service_name (PID: $pid)..."
  
  kill "$pid" 2>/dev/null
  
  # Wait for process to die
  local count=0
  while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
    sleep 1
    count=$((count + 1))
  done
  
  if kill -0 "$pid" 2>/dev/null; then
    warn "Service $service_name did not stop gracefully, forcing..."
    kill -9 "$pid" 2>/dev/null
  fi
  
  rm -f "$pid_file"
  success "Service $service_name stopped"
}

# Check health of a service
check_health() {
  local url="$1"
  local service_name=$(echo "$url" | sed 's|http://localhost:||' | sed 's|/.*||')
  
  if curl -s --max-time 5 "$url" > /dev/null 2>&1; then
    success "Health check passed for $service_name"
    return 0
  else
    warn "Health check failed for $service_name ($url)"
    return 1
  fi
}

# Start all services
start_all() {
  log "Starting all Yennefer services..."
  log "Root directory: $YENNEFER_ROOT"
  log "Log directory: $LOGS_DIR"
  
  local failed=0
  
  for service_def in "${SERVICES[@]}"; do
    if ! start_service "$service_def"; then
      failed=$((failed + 1))
    fi
  done
  
  # Wait for services to initialize
  log "Waiting for services to initialize..."
  sleep 5
  
  # Run health checks
  log "Running health checks..."
  for url in "${HEALTH_CHECKS[@]}"; do
    check_health "$url" || true
  done
  
  if [ $failed -eq 0 ]; then
    success "All services started successfully!"
  else
    warn "Started with $failed service(s) failed"
  fi
  
  echo ""
  echo "Services:"
  for service_def in "${SERVICES[@]}"; do
    local IFS=':'
    read -r -a parts <<< "$service_def"
    local service_name="${parts[0]}"
    local port="${parts[2]}"
    
    if is_running "$service_name"; then
      if [ -n "$port" ]; then
        echo "  ✅ $service_name - http://localhost:$port"
      else
        echo "  ✅ $service_name - running"
      fi
    else
      echo "  ❌ $service_name - not running"
    fi
  done
}

# Stop all services
stop_all() {
  log "Stopping all Yennefer services..."
  
  for service_def in "${SERVICES[@]}"; do
    local IFS=':'
    read -r -a parts <<< "$service_def"
    local service_name="${parts[0]}"
    stop_service "$service_name" || true
  done
  
  success "All services stopped"
}

# Show status
show_status() {
  echo ""
  log "Yennefer Services Status:"
  echo "══════════════════════════════════════════════════════════════════════"
  
  for service_def in "${SERVICES[@]}"; do
    local IFS=':'
    read -r -a parts <<< "$service_def"
    local service_name="${parts[0]}"
    local port="${parts[2]}"
    
    if is_running "$service_name"; then
      local pid=$(cat "$PIDS_DIR/${service_name}.pid")
      local uptime=$(ps -o etimes= -p "$pid" 2>/dev/null || echo "unknown")
      
      if [ -n "$port" ]; then
        local health_status=$(curl -s --max-time 3 "http://localhost:$port/health" 2>/dev/null | jq -r '.status' 2>/dev/null || echo "unknown")
        printf "  ${GREEN}✅${NC} %-20s PID: %-8s Port: %-6s Health: %s\n" "$service_name" "$pid" "$port" "$health_status"
      else
        printf "  ${GREEN}✅${NC} %-20s PID: %-8s Uptime: %ss\n" "$service_name" "$pid" "$uptime"
      fi
    else
      printf "  ${RED}❌${NC} %-20s Not running\n" "$service_name"
    fi
  done
  
  echo ""
  echo "Log files:"
  ls -lh "$LOGS_DIR" 2>/dev/null | tail -5 || echo "  No log files yet"
}

# Main
case "${1:-start}" in
  start)
    start_all
    ;;
  stop)
    stop_all
    ;;
  restart)
    stop_all
    sleep 2
    start_all
    ;;
  status)
    show_status
    ;;
  *)
    echo "Usage: $0 [start|stop|restart|status]"
    echo ""
    echo "Commands:"
    echo "  start   - Start all Yennefer services"
    echo "  stop    - Stop all Yennefer services"
    echo "  restart - Restart all Yennefer services"
    echo "  status  - Show status of all services"
    exit 1
    ;;
esac
