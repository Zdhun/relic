#!/bin/bash

# Exit on error
set -e

echo "🚀 Setting up test environment..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCANNER_DIR="$SCRIPT_DIR/services/scanner"

# Find the Python executable
if [ -f "$SCANNER_DIR/.venv/bin/python3" ]; then
    echo "📦 Using existing .venv in scanner directory..."
    PYTHON_BIN="$SCANNER_DIR/.venv/bin/python3"
elif [ -f "$SCANNER_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCANNER_DIR/.venv/bin/python"
elif [ -f "$SCRIPT_DIR/venv/bin/python3" ]; then
    echo "📦 Using root virtual environment..."
    PYTHON_BIN="$SCRIPT_DIR/venv/bin/python3"
elif [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
else
    echo "📦 Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
    PYTHON_BIN="$SCRIPT_DIR/venv/bin/python3"
fi

echo "🐍 Using Python: $PYTHON_BIN"

# Ensure all test dependencies are installed
echo "📦 Installing test dependencies..."
"$PYTHON_BIN" -m pip install -q -r "$SCANNER_DIR/requirements.txt" 2>/dev/null || true
"$PYTHON_BIN" -m pip install -q -r "$SCANNER_DIR/requirements-dev.txt" 2>/dev/null || true

echo "🧪 Running tests with coverage..."

# Run pytest with coverage from scanner directory
cd "$SCANNER_DIR"

"$PYTHON_BIN" -m pytest tests \
  --cov=app \
  --cov-report=term-missing \
  --cov-report=html:htmlcov \
  --cov-report=xml:coverage.xml \
  -v \
  "$@"

echo ""
echo "✅ Tests completed!"
echo "📊 Coverage report: $SCANNER_DIR/htmlcov/index.html"
