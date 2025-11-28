#!/bin/bash
# Start all services: Kafka, Zookeeper, MLflow, and FastAPI

echo "🚀 Starting Crypto Volatility Detection System"
echo "================================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Navigate to docker directory
cd "$(dirname "$0")"

echo "📦 Building and starting all services..."
echo "This may take a few minutes on first run."
echo ""

# Start all services
docker compose up -d --build

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

echo ""
echo "📊 Service Status:"
echo "==================="
docker compose ps

echo ""
echo "🎉 System is starting up!"
echo ""
echo "Access your services at:"
echo "  • FastAPI:        http://localhost:8000"
echo "  • API Docs:       http://localhost:8000/docs"
echo "  • Health Check:   http://localhost:8000/health"
echo "  • MLflow:         http://localhost:5001"
echo "  • Kafka:          localhost:9092"
echo ""
echo "To view logs:"
echo "  docker compose logs -f api      # API logs"
echo "  docker compose logs -f          # All logs"
echo ""
echo "To stop all services:"
echo "  docker compose down"
