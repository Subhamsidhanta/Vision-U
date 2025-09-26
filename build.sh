#!/usr/bin/env bash
# exit on error
set -o errexit

# Install system dependencies
apt-get update && apt-get install -y wkhtmltopdf

# Upgrade pip and setuptools for better compatibility
pip install --upgrade pip setuptools wheel

# Install Python dependencies (psycopg3 is pure Python - no compilation needed)
pip install -r requirements.txt
