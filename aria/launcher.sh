#!/bin/bash
# ARIA macOS App Launcher - Fixed Version
# Robust launcher with error handling and dependency checking

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="ARIA"
VERSION="0.2.1"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_error() {
    echo -e "${RED}✗ ERROR: $1${NC}" >&2
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

log_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check Python installation
check_python() {
    log_info "Checking Python installation..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found. Please install Python 3.11 or later."
        log_info "Visit: https://www.python.org/downloads/"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log_success "Found Python $PYTHON_VERSION"
    
    # Check minimum version
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
        log_error "Python 3.11+ required (found $PYTHON_VERSION)"
        exit 1
    fi
}

# Check if ARIA is already running
check_running() {
    if pgrep -f "aria-runtime" > /dev/null 2>&1; then
        log_warning "ARIA is already running (PID: $(pgrep -f 'aria-runtime' | head -1))"
        return 0
    fi
    return 1
}

# Install dependencies if needed
check_dependencies() {
    log_info "Checking Python dependencies..."
    
    REQUIRED_PACKAGES=(
        "fastapi"
        "uvicorn"
        "mlx"
        "mlx-lm"
        "pydantic"
        "psutil"
    )
    
    MISSING_PACKAGES=()
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! python3 -c "import ${package//-/_}" 2>/dev/null; then
            MISSING_PACKAGES+=("$package")
        fi
    done
    
    if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
        log_warning "Missing packages: ${MISSING_PACKAGES[@]}"
        log_info "Installing missing dependencies..."
        
        python3 -m pip install --quiet --upgrade pip
        
        for package in "${MISSING_PACKAGES[@]}"; do
            log_info "Installing $package..."
            python3 -m pip install --quiet "$package" || {
                log_error "Failed to install $package"
                exit 1
            }
        done
        
        log_success "Dependencies installed successfully"
    else
        log_success "All dependencies present"
    fi
}

# Start the runtime
start_runtime() {
    log_info "Starting ARIA runtime (v$VERSION)..."
    
    # Find the position of "ARIA.app" in the path to determine the module location
    if [[ "$SCRIPT_DIR" == *"ARIA.app"* ]]; then
        # App bundle installation
        MODULE_PATH=$(echo "$SCRIPT_DIR" | sed 's|/Contents/MacOS||')
        MODULE_PATH=$(echo "$MODULE_PATH" | sed 's|/ARIA.app||')
    else
        # Development installation
        MODULE_PATH="$SCRIPT_DIR"
    fi
    
    # Make sure we have the right path
    if [ ! -d "$MODULE_PATH/aria" ]; then
        log_error "ARIA module not found at $MODULE_PATH"
        log_info "Script directory: $SCRIPT_DIR"
        exit 1
    fi
    
    # Export PYTHONPATH
    export PYTHONPATH="$MODULE_PATH:$PYTHONPATH"
    
    log_success "Module path: $MODULE_PATH"
    
    # Change to module directory
    cd "$MODULE_PATH"
    
    # Start with aria-runtime command
    if command -v aria-runtime &> /dev/null; then
        log_success "Starting via aria-runtime command"
        exec aria-runtime --dev
    # Otherwise start via Python module
    elif python3 -m aria.aria_runtime > /dev/null 2>&1; then
        log_success "Starting via Python module"
        exec python3 -m aria.aria_runtime
    else
        log_error "Could not start ARIA runtime"
        log_info "Tried aria-runtime command and python3 -m aria.aria_runtime"
        exit 1
    fi
}

# Main execution
main() {
    clear
    echo "╔════════════════════════════════════════╗"
    echo "║  $APP_NAME Runtime Launcher v$VERSION      ║"
    echo "╚════════════════════════════════════════╝"
    echo ""
    
    # Check if already running
    if check_running; then
        log_success "Opening browser to http://localhost:8000/"
        sleep 1
        if command -v open &> /dev/null; then
            open "http://localhost:8000/" || true
        fi
        sleep 5
        exit 0
    fi
    
    # Perform checks
    check_python
    check_dependencies
    
    # Start runtime
    start_runtime
}

# Handle signals for graceful shutdown
trap 'log_info "Shutting down..."; exit 0' SIGINT SIGTERM

# Run main
main
