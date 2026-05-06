#!/bin/bash
# LightningBoost Deployment Script

set -e

echo "🚀 LightningBoost Deployment Script"
echo "===================================="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed. Please install Docker first."
    exit 1
fi

echo "✅ Docker found"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker Compose found"

# Create shared Python path
mkdir -p shared

# Build images
echo ""
echo "📦 Building Docker images..."
docker-compose build

# Start services
echo ""
echo "🎯 Starting services..."
docker-compose up -d

echo ""
echo "✅ Services started!"
echo ""
echo "📍 Access points:"
echo "   - Cloud Backend: http://localhost:8000"
echo "   - Frontend: http://localhost:8501"
echo "   - vLLM API: http://localhost:8001"
echo ""
echo "📊 Check status:"
echo "   docker-compose ps"
echo ""
echo "📋 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "⛔ Stop services:"
echo "   docker-compose down"
