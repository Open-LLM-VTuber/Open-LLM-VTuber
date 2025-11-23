#!/bin/bash
# File Sync Script for RunPod Deployment
# Sync files between your local PC and RunPod instance

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration (set these!)
RUNPOD_URL="${RUNPOD_URL:-}"          # e.g., https://abc123-12393.proxy.runpod.net
API_KEY="${API_KEY:-}"                 # Optional: your API key

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    cat << EOF
File Sync Script for RunPod Deployment

Usage: ./sync.sh [COMMAND] [OPTIONS]

Commands:
    upload <local_file> <directory>     Upload file to RunPod
    download <directory> <filename>      Download file from RunPod
    list <directory>                     List files in RunPod directory
    sync-configs                         Sync all configs to RunPod
    backup-chat                          Backup chat history from RunPod
    info                                 Show RunPod file system info

Directories:
    characters, chat_history, cache, avatars, backgrounds, configs

Environment Variables:
    RUNPOD_URL    - Your RunPod URL (e.g., https://xxx-12393.proxy.runpod.net)
    API_KEY       - Your API key (if auth is enabled)

Examples:
    # Set URL first
    export RUNPOD_URL=https://abc123-12393.proxy.runpod.net

    # Upload a character config
    ./sync.sh upload mychar.yaml characters

    # Download chat history
    ./sync.sh download chat_history conversation.json

    # List characters
    ./sync.sh list characters

    # Sync all configs
    ./sync.sh sync-configs

EOF
}

check_config() {
    if [ -z "$RUNPOD_URL" ]; then
        log_error "RUNPOD_URL not set!"
        log_info "Set it with: export RUNPOD_URL=https://your-pod-id-12393.proxy.runpod.net"
        exit 1
    fi

    # Remove trailing slash
    RUNPOD_URL="${RUNPOD_URL%/}"

    log_info "Using RunPod URL: $RUNPOD_URL"
}

upload_file() {
    local file="$1"
    local directory="$2"

    if [ ! -f "$file" ]; then
        log_error "File not found: $file"
        exit 1
    fi

    log_info "Uploading $file to $directory..."

    if [ -n "$API_KEY" ]; then
        curl -X POST -H "X-API-Key: $API_KEY" \
            -F "file=@$file" \
            "$RUNPOD_URL/api/files/upload/$directory"
    else
        curl -X POST -F "file=@$file" \
            "$RUNPOD_URL/api/files/upload/$directory"
    fi

    echo ""
    log_info "Upload complete!"
}

download_file() {
    local directory="$1"
    local filename="$2"

    log_info "Downloading $filename from $directory..."

    if [ -n "$API_KEY" ]; then
        curl -H "X-API-Key: $API_KEY" \
            -O "$RUNPOD_URL/api/files/download/$directory/$filename"
    else
        curl -O "$RUNPOD_URL/api/files/download/$directory/$filename"
    fi

    echo ""
    log_info "Download complete: $filename"
}

list_files() {
    local directory="$1"

    log_info "Listing files in $directory..."

    if [ -n "$API_KEY" ]; then
        curl -H "X-API-Key: $API_KEY" \
            "$RUNPOD_URL/api/files/list/$directory" | jq '.'
    else
        curl "$RUNPOD_URL/api/files/list/$directory" | jq '.'
    fi
}

sync_configs() {
    log_info "Syncing all configs to RunPod..."

    # Upload main config
    if [ -f "runpod/conf.yaml" ]; then
        log_info "Uploading conf.yaml..."
        upload_file "runpod/conf.yaml" "configs"
    fi

    # Upload character configs
    if [ -d "runpod/characters" ]; then
        log_info "Uploading character configs..."
        for file in runpod/characters/*.yaml; do
            if [ -f "$file" ]; then
                log_info "Uploading $(basename $file)..."
                upload_file "$file" "characters"
            fi
        done
    fi

    log_info "Config sync complete!"
}

backup_chat() {
    log_info "Backing up chat history from RunPod..."

    # Create local backup directory
    mkdir -p backups/chat_history

    # Get list of chat history files
    log_info "Fetching file list..."

    if [ -n "$API_KEY" ]; then
        files=$(curl -s -H "X-API-Key: $API_KEY" \
            "$RUNPOD_URL/api/files/list/chat_history" | jq -r '.files[].name')
    else
        files=$(curl -s "$RUNPOD_URL/api/files/list/chat_history" | jq -r '.files[].name')
    fi

    # Download each file
    for file in $files; do
        if [ "$file" != "null" ] && [ -n "$file" ]; then
            log_info "Downloading $file..."
            if [ -n "$API_KEY" ]; then
                curl -s -H "X-API-Key: $API_KEY" \
                    -o "backups/chat_history/$file" \
                    "$RUNPOD_URL/api/files/download/chat_history/$file"
            else
                curl -s -o "backups/chat_history/$file" \
                    "$RUNPOD_URL/api/files/download/chat_history/$file"
            fi
        fi
    done

    log_info "Backup complete! Saved to backups/chat_history/"
}

show_info() {
    log_info "Getting RunPod file system info..."

    if [ -n "$API_KEY" ]; then
        curl -H "X-API-Key: $API_KEY" \
            "$RUNPOD_URL/api/files/info" | jq '.'
    else
        curl "$RUNPOD_URL/api/files/info" | jq '.'
    fi
}

# Main script
case "${1:-help}" in
    upload)
        check_config
        upload_file "$2" "$3"
        ;;
    download)
        check_config
        download_file "$2" "$3"
        ;;
    list)
        check_config
        list_files "$2"
        ;;
    sync-configs)
        check_config
        sync_configs
        ;;
    backup-chat)
        check_config
        backup_chat
        ;;
    info)
        check_config
        show_info
        ;;
    help|*)
        show_help
        ;;
esac
