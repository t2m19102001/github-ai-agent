#!/bin/bash
# One-command deployment script

set -e

echo "🚀 GitHub AI Agent - One-Command Deploy"
echo "======================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env and add your API keys:"
    echo "   - GROQ_API_KEY"
    echo "   - GITHUB_TOKEN"
    echo ""
    read -p "Press Enter after updating .env file..."
fi

# Build and start
echo "🔨 Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Health check
echo ""
echo "🏥 Health check..."
if curl -f http://localhost:5000/ > /dev/null 2>&1; then
    echo "✅ Service is healthy!"
else
    echo "❌ Service health check failed. Check logs:"
    echo "   docker-compose logs github-ai-agent"
    exit 1
fi

echo ""
echo "======================================"
echo "✅ Deployment complete!"
echo ""
echo "🌐 Access the application:"
echo "   http://localhost:5000"
echo ""
echo "📊 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose down"
echo "======================================"
