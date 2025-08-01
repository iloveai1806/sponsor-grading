#!/bin/bash

# run_daily.sh - Daily sponsor grading automation script
# This script sets up the environment, installs dependencies, and runs sponsor grading

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/sponsor_grader_$(date +%Y%m%d_%H%M%S).log"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
SPONSOR_GRADER="$SCRIPT_DIR/sponsor_grader.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Create logs directory
mkdir -p "$LOG_DIR"

log "Starting daily sponsor grading process..."
log "Script directory: $SCRIPT_DIR"

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    error "Python3 is not installed or not in PATH"
    exit 1
fi

log "Python3 version: $(python3 --version)"

# Check if required files exist
if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    error "Requirements file not found: $REQUIREMENTS_FILE"
    exit 1
fi

if [[ ! -f "$SPONSOR_GRADER" ]]; then
    error "Sponsor grader script not found: $SPONSOR_GRADER"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    success "Virtual environment created"
else
    log "Virtual environment already exists"
fi

# Activate virtual environment
log "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
log "Upgrading pip..."
pip install --upgrade pip >> "$LOG_FILE" 2>&1

# Install/update requirements
log "Installing requirements from $REQUIREMENTS_FILE..."
pip install -r "$REQUIREMENTS_FILE" >> "$LOG_FILE" 2>&1
success "Requirements installed successfully"

# Check if .env file exists (for configuration)
if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
    warning ".env file not found. Make sure environment variables are set:"
    warning "- OPENAI_API_KEY"
    warning "- GOOGLE_SHEETS_CREDENTIALS_PATH"
    warning "- GOOGLE_SHEETS_ID"
fi

# Run sponsor grader with different options based on arguments
if [[ $# -eq 0 ]]; then
    # Default: process media sheet with max 10 records for safety
    log "Running sponsor grader (default: media sheet, max 10 records)..."
    python3 "$SPONSOR_GRADER" --sheet-type media --max-records 10 2>&1 | tee -a "$LOG_FILE"
else
    # Pass all arguments to the sponsor grader
    log "Running sponsor grader with arguments: $*"
    python3 "$SPONSOR_GRADER" "$@" 2>&1 | tee -a "$LOG_FILE"
fi

GRADER_EXIT_CODE=$?

# Deactivate virtual environment
deactivate

# Check if sponsor grader ran successfully
if [[ $GRADER_EXIT_CODE -eq 0 ]]; then
    success "Sponsor grading completed successfully"
    log "Log file: $LOG_FILE"
else
    error "Sponsor grading failed with exit code: $GRADER_EXIT_CODE"
    exit $GRADER_EXIT_CODE
fi

# Clean up old log files (keep last 30 days)
log "Cleaning up old log files..."
find "$LOG_DIR" -name "sponsor_grader_*.log" -mtime +30 -delete 2>/dev/null || true

success "Daily sponsor grading process completed!"

# Display usage instructions
cat << EOF

========================================
USAGE INSTRUCTIONS
========================================

1. Make script executable:
   chmod +x run_daily.sh

2. Run manually:
   ./run_daily.sh                          # Default: media sheet, max 10 records
   ./run_daily.sh --sheet-type blog        # Process blog sheet
   ./run_daily.sh --max-records 5          # Limit to 5 records
   ./run_daily.sh --sheet-type blog --max-records 20  # Custom options

3. Schedule daily execution with cron:
   # Edit crontab
   crontab -e
   
   # Add this line to run daily at 9 AM:
   0 9 * * * /path/to/sponsor-grading/run_daily.sh >> /path/to/sponsor-grading/logs/cron.log 2>&1
   
   # Or run every weekday at 2 PM:
   0 14 * * 1-5 /path/to/sponsor-grading/run_daily.sh

4. View logs:
   tail -f logs/sponsor_grader_*.log       # Follow latest log
   ls -la logs/                            # List all log files

========================================
EOF 