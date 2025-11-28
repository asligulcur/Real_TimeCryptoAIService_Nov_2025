#!/bin/bash
# Start the FastAPI service locally
# Usage: ./start_api.sh

echo "🚀 Starting Crypto Volatility API..."
echo ""

# Change to api directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo "⚠️  Warning: No virtual environment found"
    echo "Run: python3 -m venv venv && source venv/bin/activate"
fi

# Install dependencies if needed
echo "📦 Installing dependencies..."
pip install -q -r ../requirements.txt

echo ""
echo "✅ Starting FastAPI server on http://localhost:8000"
echo "📖 API docs available at http://localhost:8000/docs"
echo ""

# Start uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
