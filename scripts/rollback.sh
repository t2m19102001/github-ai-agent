#!/bin/bash
# Rollback deployment script

set -e

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: ./scripts/rollback.sh <version>"
    exit 1
fi

echo "🔄 Rolling back to version: $VERSION"
echo "======================================"
echo ""

# Stop current deployment
echo "🛑 Stopping current deployment..."
docker-compose down

echo ""
echo "📥 Pulling previous version: $VERSION"
docker pull $VERSION

echo ""
echo "🚀 Starting rollback deployment..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Health check
echo ""
echo "🏥 Health check..."
if curl -f http://localhost:5000/ > /dev/null 2>&1; then
    echo "✅ Rollback successful!"
else
    echo "❌ Rollback health check failed. Check logs:"
    echo "   docker-compose logs"
    exit 1
fi

echo ""
echo "======================================"
echo "✅ Rollback complete!"
echo ""
