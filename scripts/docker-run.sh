#!/bin/bash
# scripts/docker-run.sh - Easy Docker execution for Super MCP Server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Super MCP Server Docker Runner"
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Parse command line arguments
COMMAND=${1:-"run"}
SERVICE=${2:-"mcp-server"}

case $COMMAND in
    "build")
        echo "🔨 Building Docker image..."
        cd "$PROJECT_ROOT"
        docker build -t super-mcp-server .
        echo "✅ Build complete!"
        ;;
    
    "run")
        echo "🔨 Building and running Super MCP Server..."
        cd "$PROJECT_ROOT"
        docker-compose up --build $SERVICE
        ;;
    
    "dev")
        echo "🛠️ Starting development environment..."
        cd "$PROJECT_ROOT"
        docker-compose --profile dev up --build dev
        ;;
    
    "test")
        echo "🧪 Running tests in container..."
        cd "$PROJECT_ROOT"
        docker build -t super-mcp-test --target builder .
        docker run --rm -v "$PROJECT_ROOT:/app" super-mcp-test \
            /bin/bash -c "cd /app && pip install -r requirements-dev.txt && python -m pytest tests/ -v"
        ;;
    
    "shell")
        echo "🐚 Opening shell in container..."
        cd "$PROJECT_ROOT"
        docker-compose run --rm dev /bin/bash
        ;;
    
    "clean")
        echo "🧹 Cleaning up Docker resources..."
        cd "$PROJECT_ROOT"
        docker-compose down --volumes --remove-orphans
        docker system prune -f
        echo "✅ Cleanup complete!"
        ;;
    
    "logs")
        echo "📋 Showing container logs..."
        cd "$PROJECT_ROOT"
        docker-compose logs -f $SERVICE
        ;;
    
    *)
        echo "Usage: $0 {build|run|dev|test|shell|clean|logs} [service]"
        echo ""
        echo "Commands:"
        echo "  build  - Build the Docker image"
        echo "  run    - Build and run the MCP server (default)"
        echo "  dev    - Start development environment"
        echo "  test   - Run tests in container"
        echo "  shell  - Open shell in development container"
        echo "  clean  - Clean up Docker resources"
        echo "  logs   - Show container logs"
        echo ""
        echo "Services:"
        echo "  mcp-server - Production MCP server (default)"
        echo "  dev        - Development container"
        exit 1
        ;;
esac