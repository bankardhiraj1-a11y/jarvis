#!/bin/bash

# JARVIS 2 - AUTONOMOUS AI TRADING PLATFORM
# Launch Script - Best in Class Self-Learning, Self-Healing System
# Status: PRODUCTION READY

set -e

echo "=========================================="
echo "🚀 JARVIS 2 LAUNCH SEQUENCE"
echo "=========================================="
echo ""

# Check prerequisites
echo "✓ Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install Docker and try again."
    exit 1
fi
echo "✓ Docker found"

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Install Docker Compose and try again."
    exit 1
fi
echo "✓ Docker Compose found"

# Check DhanHQ credentials
if [ -z "$DHAN_CLIENT_ID" ] && [ ! -f "backend/.env" ]; then
    echo ""
    echo "⚠️  DhanHQ credentials not found."
    echo "Set environment variables or create backend/.env:"
    echo "  export DHAN_CLIENT_ID='your_client_id'"
    echo "  export DHAN_ACCESS_TOKEN='your_token'"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "🛠️  BUILDING DOCKER IMAGES"
echo "=========================================="
echo ""

# Build images
docker-compose build --no-cache

echo ""
echo "=========================================="
echo "🚀 STARTING SERVICES"
echo "=========================================="
echo ""

# Start services
docker-compose up -d

echo ""
echo "⏳ Waiting for services to initialize..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "running"; then
    echo ""
    echo "=========================================="
    echo "✅ JARVIS 2 IS LIVE"
    echo "=========================================="
    echo ""
    echo "🌐 Frontend:     http://localhost:3000"
    echo "🔌 Backend API:  http://localhost:8000"
    echo "📊 API Docs:     http://localhost:8000/docs"
    echo "💾 Database:     PostgreSQL on port 5432"
    echo ""
    echo "📈 Monitoring:"
    echo "   • Watch logs:     docker-compose logs -f backend"
    echo "   • Status:         curl http://localhost:8000/optimizer/status"
    echo "   • Progress:       curl http://localhost:8000/optimizer/progress"
    echo "   • Dashboard:      http://localhost:3000"
    echo ""
    echo "🤖 System Status:"
    echo "   • Mode: AUTONOMOUS OPTIMIZATION (until 90%)"
    echo "   • Boss Agent: ACTIVE"
    echo "   • Cycles: Running every 5 minutes"
    echo "   • Target: 90%+ win rate across all agents"
    echo "   • Timeline: Until victory achieved"
    echo ""
    echo "=========================================="
    echo "✨ BEST IN CLASS SELF-LEARNING, SELF-HEALING PLATFORM LIVE ✨"
    echo "=========================================="
    echo ""
    echo "🎯 Keep laptop ON. Internet ON. DhanHQ token active."
    echo "   Everything else is 100% autonomous."
    echo ""
    echo "📺 Watch live:"
    echo "   docker-compose logs -f backend | grep -E '(CYCLE|PHASE|✓|⚠|🎯)'
    echo ""
else
    echo "❌ Failed to start services. Check logs:"
    docker-compose logs
    exit 1
fi

# Keep running
docker-compose logs -f backend
