#!/usr/bin/env bash
# exit on error
set -o errexit

# Install system dependencies
apt-get update && apt-get install -y wkhtmltopdf

# Upgrade pip first
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
