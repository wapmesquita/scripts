#!/bin/bash

# Initialize glacier-outputs repository as a subrepo
# This script creates/updates the outputs directory with the specified GitHub repository

set -e

# Default values
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OUTPUTS_DIR="${SCRIPT_DIR}/outputs"
REPO_URL=""

# Function to display usage information
usage() {
    echo "Usage: $0 --repo-url <repository-url> [--output-dir <directory>]"
    echo ""
    echo "Options:"
    echo "  --repo-url, -r    Required. URL of the Git repository to initialize"
    echo "  --output-dir, -o  Optional. Directory to initialize the repository (default: ./outputs)"
    echo "  --help, -h        Display this help message and exit"
    echo ""
    echo "Example:"
    echo "  $0 --repo-url https://github.com/wapmesquita/glacier-outputs.git"
    echo "  $0 -r https://github.com/wapmesquita/glacier-outputs.git -o /custom/path"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    
    case $key in
        --repo-url|-r)
            REPO_URL="$2"
            shift 2
            ;;
        --output-dir|-o)
            OUTPUTS_DIR="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check if repo URL was provided
if [ -z "$REPO_URL" ]; then
    echo "Error: Repository URL is required"
    usage
    exit 1
fi

echo "Initializing repository in ${OUTPUTS_DIR}"
echo "Using repository: ${REPO_URL}"

# Create the outputs directory if it doesn't exist
if [ ! -d "${OUTPUTS_DIR}" ]; then
    echo "Creating outputs directory..."
    mkdir -p "${OUTPUTS_DIR}"
fi

# Check if it's already a git repository
if [ -d "${OUTPUTS_DIR}/.git" ]; then
    echo "Repository already initialized. Updating..."
    cd "${OUTPUTS_DIR}"
    git pull origin main || echo "Failed to pull latest changes. The repository might need attention."
else
    echo "Initializing new repository..."
    cd "${OUTPUTS_DIR}"
    git init
    git remote add origin "${REPO_URL}"
    
    # Try to pull the repository (it might be empty)
    if ! git pull origin main; then
        echo "Could not pull from remote. Creating initial commit..."
        echo "# Glacier Outputs" > README.md
        echo "This repository contains output files from Glacier operations." >> README.md
        git add README.md
        git commit -m "Initial commit"
        
        echo "Attempting to push initial commit..."
        if git push -u origin main; then
            echo "Initial commit pushed successfully."
        else
            echo "Could not push initial commit. The repository might need manual setup."
            echo "Please ensure you have the correct permissions and the repository exists."
        fi
    fi
fi

echo ""
echo "Repository initialized at ${OUTPUTS_DIR}"
echo "You can now store glacier output files in this directory and use git commands"
echo "to commit and push changes to ${REPO_URL}"
echo ""
echo "Quick commands:"
echo "  cd ${OUTPUTS_DIR}"
echo "  git status                   # Check status"
echo "  git add .                    # Stage all changes"
echo "  git commit -m 'Message'      # Commit changes"
echo "  git push                     # Push to GitHub"
