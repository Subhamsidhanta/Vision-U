#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade pip first
pip install --upgrade pip

# Install system dependencies for PostgreSQL
apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    wkhtmltopdf

# Install Python dependencies
pip install -r requirements.txt
