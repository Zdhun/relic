#!/bin/bash

# Exit on error
set -e

echo "🚀 Setting up test environment..."

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dev dependencies if needed
if [ -f "services/scanner/requirements-dev.txt" ]; then
    pip install -q -r services/scanner/requirements-dev.txt
fi

# Install app dependencies if needed (for imports to work)
if [ -f "services/scanner/requirements.txt" ]; then
    pip install -q -r services/scanner/requirements.txt
fi

echo "🧪 Running tests with coverage..."

# Run pytest with coverage
# We run it from the services/scanner directory context
cd services/scanner
# Ensure we use the python from venv (which is active)
python -m pytest tests \
  --cov=app \
  --cov-report=term-missing \
  --cov-report=html:htmlcov \
  --cov-report=xml:coverage.xml \
  -v

echo "✅ Tests completed!"
