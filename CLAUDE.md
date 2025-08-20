# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

S3 Super MCP Server is a Model Context Protocol server that enables LLMs to perform Business Intelligence analytics on S3 data using the [super](https://github.com/brimdata/super) library. The server converts natural language business questions into SuperSQL queries and executes them against data stored in Amazon S3.

**Key Architecture**: The super binary runs server-side only (AWS Lambda, Docker, etc.). MCP clients like Claude Desktop communicate via MCP protocol without needing super installed locally.

## Development Commands

### Core Development
```bash
# Install dependencies
pip install -r requirements.txt

# Install development dependencies  
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# Format code
black src/ tests/
isort src/ tests/

# Lint code
ruff check src/ tests/
mypy src/

# Run the MCP server locally
python src/mcp_server.py
```

### AWS Deployment
```bash
# Build and deploy with SAM
sam build
sam deploy --guided

# Deploy specific environment
./scripts/deploy.sh production
```

### Super Binary Management
```bash
# Verify super installation (development)
which super
super --version

# Test S3 access
aws s3 ls s3://your-bucket/
aws sts get-caller-identity
```

## Architecture Overview

### Core Components
- **MCP Server** (`src/mcp_server.py`): FastMCP server handling MCP protocol and Lambda deployment
- **Query Processor** (`src/query_processor.py`): Converts natural language to SuperSQL queries  
- **Super Executor** (`src/super_executor.py`): Executes super binary commands server-side
- **S3 Helper** (`src/s3_helper.py`): S3 operations and path validation

### MCP Tools (API Interface)
1. **query_s3_data**: Execute natural language queries against S3 data
2. **explore_s3_data**: Discover data structure and schema
3. **list_s3_files**: Browse available S3 data sources

### Deployment Architecture
- **Server-Side**: Super binary installed on Lambda/container infrastructure
- **Client-Side**: MCP clients connect via protocol, no super binary required
- **Lambda Layer**: Contains super binary at `/opt/bin/super`

## Key Technologies

- **FastMCP**: Python MCP server framework
- **Super Library**: Data analytics engine (server-side execution only)
- **AWS Lambda**: Primary deployment target with custom layer
- **Boto3**: AWS S3 integration
- **Pydantic**: Data validation and settings

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPER_BINARY_PATH` | Path to super binary | `/opt/bin/super` |
| `AWS_REGION` | AWS region for S3 access | `us-east-1` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `QUERY_TIMEOUT` | Query timeout in seconds | `300` |
| `MAX_RESULTS` | Maximum results per query | `10000` |

## Testing Approach

- **Unit Tests**: Query processing, SuperSQL generation, error handling
- **Integration Tests**: End-to-end query scenarios, S3 access, Lambda deployment
- **Test Framework**: pytest with asyncio support
- **Mocking**: moto for AWS services, custom fixtures for super binary simulation

## Critical Dependencies

- Super binary must be executable at runtime on server infrastructure
- AWS credentials with S3 read permissions required  
- Python 3.11+ for modern async/await patterns
- FastMCP library for MCP protocol compliance

## Common Query Patterns

The server recognizes these business query patterns:
- **Top N Analysis**: "top 10 products by sales"
- **Time Series**: "revenue by month" 
- **Filtering**: "errors from API service"
- **Aggregation**: "average response time by endpoint"
- **Counting**: "how many users signed up today"

## Performance Considerations

- Query timeout: 300 seconds maximum
- Memory limit: 1024MB for Lambda deployment
- Supports concurrent requests
- Optimized for datasets up to 1GB per query
- Use specific S3 paths to reduce data scanning