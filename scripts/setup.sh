#!/bin/bash

echo "Gil Vicente Tactical Intelligence Platform - Setup Script"
echo "=============================================================="
echo ""

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "OK: Docker and Docker Compose found"
echo ""

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "INFO: Creating .env file from template..."
    cp .env.example .env
    echo ""
fi

# Build and start services
echo "Starting services..."
docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "OK: Setup complete!"
    echo ""
    echo "Access the application:"
    echo "   - Frontend Dashboard: http://localhost:3000"
    echo "   - Backend API: http://localhost:8000"
    echo "   - API Documentation: http://localhost:8000/docs"
    echo ""
    echo "Next steps:"
    echo "   1. (Optional) Configure SofaScore settings in .env"
    echo "   2. (Optional) Run the scraper for offline data: python3 scrapper/scrapper.py"
    echo "   3. Restart services: docker-compose restart"
    echo "   4. View logs: docker-compose logs -f"
    echo ""
else
    echo ""
    echo "ERROR: Some services failed to start. Check logs with:"
    echo "   docker-compose logs"
    echo ""
fi
