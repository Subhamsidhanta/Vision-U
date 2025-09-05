#!/usr/bin/env bash
# exit on error
set -o errexit

# Update & install system dependencies
apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    wkhtmltopdf

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
