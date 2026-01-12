#!/bin/bash
set -e

# Creativity Pipeline Entrypoint Script

echo "================================================"
echo "  Creativity Pipeline - Starting..."
echo "  Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Timezone: ${TZ:-UTC}"
echo "================================================"

# Ensure vault directories exist
mkdir -p /vault/cards /vault/ideas /vault/experiments /vault/archive

# Check required environment variables
check_env() {
    if [ -z "${!1}" ]; then
        echo "Warning: $1 is not set"
        return 1
    fi
    return 0
}

echo ""
echo "Checking configuration..."

# Required for full functionality
check_env "ANTHROPIC_API_KEY" || echo "  - AI features will be disabled"
check_env "DINGTALK_CLIENT_ID" || echo "  - DingTalk notifications will be disabled"

echo ""
echo "Vault path: ${VAULT_PATH:-/vault}"
echo "Schedule:"
echo "  - Morning:   ${MORNING_PUSH_TIME:-09:00}"
echo "  - Afternoon: ${AFTERNOON_PUSH_TIME:-14:00}"
echo "  - Evening:   ${EVENING_PUSH_TIME:-21:30}"
echo ""

# Handle different run modes
case "${1:-scheduler}" in
    scheduler)
        echo "Starting scheduler mode with supercronic..."
        exec supercronic /app/crontab
        ;;

    once)
        echo "Running single execution..."
        exec python -m src.main --mode once
        ;;

    morning)
        echo "Triggering morning push..."
        exec python -m src.main --touch-point morning
        ;;

    afternoon)
        echo "Triggering afternoon push..."
        exec python -m src.main --touch-point afternoon
        ;;

    evening)
        echo "Triggering evening push..."
        exec python -m src.main --touch-point evening
        ;;

    shell)
        echo "Starting interactive shell..."
        exec /bin/bash
        ;;

    *)
        echo "Unknown command: $1"
        echo "Available commands: scheduler, once, morning, afternoon, evening, shell"
        exit 1
        ;;
esac
