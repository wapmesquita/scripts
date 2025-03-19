#!/bin/bash -xe

# Push glacier log files to the outputs repository

set -e

# Script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OUTPUTS_DIR="${1:-${SCRIPT_DIR}/outputs}"
LOG_PATTERN="*.log"

# Check if outputs directory exists and is a git repository
if [ ! -d "${OUTPUTS_DIR}/.git" ]; then
    echo "Outputs repository not initialized. Run init_outputs_repo.sh first"
fi

cd "${OUTPUTS_DIR}"

# Find log files
LOG_FILES=$(find "${OUTPUTS_DIR}" -maxdepth 1 -name "${LOG_PATTERN}")

# Check if any log files were found
if [ -z "${LOG_FILES}" ]; then
    echo "No log files found in ${SCRIPT_DIR}"
    exit 0
fi

# Commit and push changes
git add .
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
git commit -m "Add glacier logs - ${TIMESTAMP}"

echo "Pushing changes to remote repository..."
if git push; then
    echo "Successfully pushed logs to repository"
else
    echo "Failed to push logs. You may need to resolve conflicts or check permissions."
fi
