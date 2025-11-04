#!/bin/bash
# Setup script for LLM Quiz Solver

set -euo pipefail

echo "=== LLM Quiz Solver Setup ==="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "Python 3 not found. Please install Python 3.8+"; exit 1; }

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers (this may take a moment)..."
playwright install chromium

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and set your SECRET and EMAIL"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and set SECRET and EMAIL"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Run the server: python run.py"
echo "4. Test the API: python example_usage.py"

