# Glacier Outputs Repository Integration

This document describes how to use the integration with the repository for storing log files and other output artifacts.

## Overview

The integration provides a way to automatically push output files from Glacier to a dedicated GitHub repository for storage and tracking.

## Shell Scripts

### Initialize Repository

You can use the `init_outputs_repo.sh` script to set up the outputs repository:

```bash
# Make the script executable
chmod +x init_outputs_repo.sh

# Initialize with the required repository URL
./init_outputs_repo.sh --repo-url [repo-url]

# For custom output directory
./init_outputs_repo.sh --repo-url [repo-url] --output-dir /custom/path
```

This will:
- Create an "outputs" directory in your glacier folder (or the specified custom path)
- Initialize it as a Git repository
- Connect it to the remote GitHub repository

### Push Log Files

You can use the `push_to_outputs_repo.sh` script to quickly push log files:

```bash
# Make the script executable
chmod +x push_to_outputs_repo.sh

# Push all log files to the repository
./push_to_outputs_repo.sh

# For custom output directory
./push_to_outputs_repo.sh /custom/path
```

This will:
- Find all files matching the given pattern in the specified directory (default: ./outputs)
- Copy them to the outputs repository
- Commit and push them to GitHub
