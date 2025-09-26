#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Install wkhtmltopdf for PDF generation
apt-get update && apt-get install -y wkhtmltopdf
