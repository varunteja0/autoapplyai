#!/usr/bin/env bash
set -euo pipefail

echo "=== AutoApplyAI Setup ==="

# Check prerequisites
echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed."; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed."; exit 1; }

# Create .env from example if doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "WARNING: Update .env with your actual configuration values!"
fi

# Build and start services
echo "Building Docker images..."
docker compose build

echo "Starting services..."
docker compose up -d db redis
sleep 5

echo "Running database migrations..."
docker compose run --rm backend alembic upgrade head

echo "Starting all services..."
docker compose up -d

echo ""
echo "=== AutoApplyAI is running! ==="
echo "Backend API:    http://localhost:8000"
echo "API Docs:       http://localhost:8000/docs"
echo "Frontend:       http://localhost:5173"
echo "Flower:         http://localhost:5555"
echo ""
echo "Run 'docker compose logs -f' to view logs"
echo "Run 'docker compose down' to stop all services"
