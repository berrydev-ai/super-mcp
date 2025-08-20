# Development Guide

This guide shows how to develop and run the Super MCP Server locally using devcontainers or Docker.

## Prerequisites

- Docker Desktop installed and running
- VS Code with Dev Containers extension (for devcontainer approach)
- AWS credentials configured locally (optional, for S3 testing)

## Option 1: VS Code DevContainer (Recommended)

### Quick Start

1. **Open in VS Code**:
   ```bash
   code .
   ```

2. **Reopen in Container**:
   - VS Code will detect the devcontainer configuration
   - Click "Reopen in Container" when prompted
   - Or use Command Palette: `Dev Containers: Reopen in Container`

3. **Wait for Setup**:
   - Container builds automatically (first time takes ~5 minutes)
   - Post-create command runs setup script
   - Extensions install automatically

4. **Verify Installation**:
   ```bash
   # In VS Code terminal
   super --version
   python --version
   ```

### Development Workflow

1. **Run Tests**:
   ```bash
   pytest tests/ -v
   ```

2. **Start MCP Server**:
   ```bash
   python src/mcp_server.py
   ```

3. **Format Code**:
   ```bash
   black src/ tests/
   isort src/ tests/
   ```

4. **Lint Code**:
   ```bash
   ruff check src/ tests/
   mypy src/
   ```

### AWS Configuration

If testing with real S3 data:

1. **Mount AWS credentials** (automatic via devcontainer config):
   - Your local `~/.aws` folder is mounted read-only
   - No additional setup needed if you have AWS CLI configured

2. **Test S3 access**:
   ```bash
   aws s3 ls s3://your-bucket/
   aws sts get-caller-identity
   ```

## Option 2: Docker Compose

### Quick Start

1. **Use the Docker runner script**:
   ```bash
   # Run in production mode
   ./scripts/docker-run.sh run

   # Run in development mode
   ./scripts/docker-run.sh dev

   # Run tests
   ./scripts/docker-run.sh test

   # Open shell for debugging
   ./scripts/docker-run.sh shell
   ```

### Manual Docker Commands

1. **Build and run**:
   ```bash
   docker-compose up --build
   ```

2. **Development mode**:
   ```bash
   docker-compose --profile dev up --build dev
   ```

3. **Run tests**:
   ```bash
   docker-compose run --rm dev python -m pytest tests/ -v
   ```

## Testing the MCP Server

### Basic Functionality Test

Once running, test the MCP tools:

1. **Check health**:
   ```bash
   curl http://localhost:8080/health
   ```

2. **Test super binary**:
   ```bash
   # In container
   super --version
   ```

### Sample MCP Queries

The server exposes these MCP tools:

1. **query_s3_data**: Execute natural language queries
2. **explore_s3_data**: Discover data structure
3. **list_s3_files**: Browse S3 data sources

Example usage with MCP client:
```json
{
  "method": "tools/call",
  "params": {
    "name": "query_s3_data",
    "arguments": {
      "query": "Show me the top 10 products by sales",
      "s3_path": "s3://my-bucket/sales-data/"
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Super binary not found**:
   - Rebuild container: `./scripts/docker-run.sh clean && ./scripts/docker-run.sh build`
   - Check binary path: `which super` in container

2. **AWS credentials not working**:
   - Verify local AWS setup: `aws sts get-caller-identity`
   - Check mounted credentials: `ls -la ~/.aws` in container

3. **Port already in use**:
   - Stop other containers: `docker-compose down`
   - Change ports in `docker-compose.yml`

4. **Container build fails**:
   - Check Docker daemon is running
   - Clear Docker cache: `docker system prune -f`

### Debug Commands

```bash
# View container logs
./scripts/docker-run.sh logs

# Clean Docker resources
./scripts/docker-run.sh clean

# Shell into running container
docker exec -it super-mcp-server /bin/bash

# Check container status
docker-compose ps
```

### Performance Tips

- Use Docker BuildKit for faster builds:
  ```bash
  export DOCKER_BUILDKIT=1
  ```

- Bind mount source code in development for instant changes:
  ```bash
  docker-compose --profile dev up dev
  ```

## Environment Variables

Key environment variables for development:

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPER_BINARY_PATH` | `/usr/local/bin/super` | Path to super binary |
| `AWS_DEFAULT_REGION` | `us-east-1` | AWS region for S3 |
| `LOG_LEVEL` | `DEBUG` | Logging verbosity in dev |
| `QUERY_TIMEOUT` | `300` | Query timeout seconds |
| `MAX_RESULTS` | `10000` | Max results per query |

Set in `docker-compose.yml` or pass to container:
```bash
docker run -e LOG_LEVEL=INFO super-mcp-server
```