#!/usr/bin/env bash
# exit on error
set -o errexit

# Install system dependencies for PDF generation
apt-get update && apt-get install -y wkhtmltopdf xvfb

# Upgrade pip and setuptools for better compatibility  
pip install --upgrade pip setuptools wheel

# Install Python dependencies
pip install -r requirements.txt

echo "✅ Build completed successfully!"
echo "📊 Python version: $(python --version)"
echo "🗄️ Dependencies installed: $(pip list | wc -l) packages"
