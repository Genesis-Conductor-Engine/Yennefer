#!/bin/bash
# Yennefer Health Check Script
# Monitors all Yennefer services and reports status
# Usage: bash health_check.sh [--json] [--loop] [--interval N]

set -e

YENNEFER_ROOT="/home/diamondnode/Yennefer"
PIDS_DIR="$YENNEFER_ROOT/.pids"
JSON_OUTPUT=false
LOOP_MODE=false
INTERVAL=60

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      JSON_OUTPUT=true
      shift
      ;;
    --loop)
      LOOP_MODE=true
      shift
      ;;
    --interval)
      INTERVAL="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Service health checks
declare -A SERVICE_CHECKS=(
  ["diamond-vault"]="http://localhost:8100/health"
  ["soul-api"]="http://localhost:8088/api/soul"
  ["qmem-gateway"]="http://localhost:8003/api/health"
  ["process-guardian"]=""
  ["conductor"]=""
  ["qmcp-bridge"]=""
  ["qmcp-bridge-node"]=""
)

# Check if service is running
is_running() {
  local service_name="$1"
  local pid_file="$PIDS_DIR/${service_name}.pid"
  
  if [ -f "$pid_file" ]; then
    local pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      echo "$pid"
      return 0
    fi
  fi
  return 1
}

# Check service health
check_service() {
  local service_name="$1"
  local health_url="${SERVICE_CHECKS[$service_name]}"
  local status="stopped"
  local details=""
  
  if pid=$(is_running "$service_name"); then
    status="running"
    details="PID: $pid"
    
    # If there's a health endpoint, check it
    if [ -n "$health_url" ]; then
      if response=$(curl -s --max-time 5 "$health_url" 2>/dev/null); then
        local http_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$health_url" 2>/dev/null)
        if [ "$http_status" -ge 200 ] && [ "$http_status" -lt 400 ]; then
          status="healthy"
          # Try to extract version or other info
          if echo "$response" | jq -e '.status' > /dev/null 2>&1; then
            details="$details, Status: $(echo "$response" | jq -r '.status')"
          elif echo "$response" | jq -e '.breath' > /dev/null 2>&1; then
            local breath=$(echo "$response" | jq -r '.breath // "N/A"')
            local coherence=$(echo "$response" | jq -r '.coherence // "N/A"')
            details="$details, Breath: $breath tokens, Coherence: $coherence%"
          fi
        else
          status="unhealthy"
          details="$details, HTTP: $http_status"
        fi
      else
        status="degraded"
        details="$details, Health check timeout"
      fi
    fi
  fi
  
  if [ "$JSON_OUTPUT" = true ]; then
    echo "{\"service\": \"$service_name\", \"status\": \"$status\", \"details\": \"$details\"}"
  else
    printf "%-20s %12s %s\n" "$service_name" "$status" "$details"
  fi
}

# Output header
output_header() {
  if [ "$JSON_OUTPUT" = true ]; then
    echo "["
  else
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║              YENNEFER HEALTH MONITOR                             ║"
    echo "║            $(date '+%Y-%m-%d %H:%M:%S')                               ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
    printf "%-20s %12s %s\n" "SERVICE" "STATUS" "DETAILS"
    echo "─────────────────────────────────────────────────────────────────────"
  fi
}

output_footer() {
  if [ "$JSON_OUTPUT" = true ]; then
    echo "]"
  else
    echo "─────────────────────────────────────────────────────────────────────"
    echo ""
  fi
}

# Main check function
run_checks() {
  output_header
  
  local first=true
  for service in "${!SERVICE_CHECKS[@]}"; do
    if [ "$JSON_OUTPUT" = true ]; then
      if [ "$first" = true ]; then
        first=false
      else
        echo ","
      fi
    fi
    check_service "$service"
  done
  
  output_footer
}

# Summary statistics
get_summary() {
  local total=0
  local healthy=0
  local running=0
  local stopped=0
  local unhealthy=0
  
  for service in "${!SERVICE_CHECKS[@]}"; do
    total=$((total + 1))
    local status=$(check_service "$service" 2>/dev/null | awk '{print $2}')
    
    case "$status" in
      healthy) healthy=$((healthy + 1)) ;;
      running) running=$((running + 1)) ;;
      stopped) stopped=$((stopped + 1)) ;;
      unhealthy|degraded) unhealthy=$((unhealthy + 1)) ;;
    esac
  done
  
  echo ""
  echo "Summary: $healthy healthy, $running running, $unhealthy unhealthy, $stopped stopped (total: $total)"
}

# Main execution
if [ "$LOOP_MODE" = true ]; then
  echo "Starting health check loop (interval: ${INTERVAL}s)..."
  echo "Press Ctrl+C to stop"
  
  while true; do
    clear
    run_checks
    get_summary
    sleep "$INTERVAL"
  done
else
  run_checks
  get_summary
fi
