# S3 Super MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![AWS Lambda Ready](https://img.shields.io/badge/AWS%20Lambda-Ready-orange.svg)](https://aws.amazon.com/lambda/)

A Model Context Protocol (MCP) server that enables Large Language Models to perform sophisticated Business Intelligence analytics on data stored in Amazon S3 using the powerful [super](https://github.com/brimdata/super) library.

## Overview

The S3 Super MCP Server bridges the gap between natural language queries and complex data analytics. It allows AI assistants like Claude Desktop to understand business questions in plain English and automatically convert them into optimized SuperSQL queries that can analyze massive datasets stored in S3.

### Key Features

- **Natural Language Processing**: Convert business questions into SQL queries automatically
- **Multi-Format Support**: Query JSON, CSV, Parquet, and other formats seamlessly
- **Business Intelligence Templates**: Pre-built analytics for revenue, customer analysis, churn prediction
- **High Performance**: Leverages super's optimized query engine for fast results
- **Serverless Ready**: Deploy to AWS Lambda for automatic scaling
- **Production Grade**: Comprehensive error handling, monitoring, and security

### Use Cases

- **Executive Dashboards**: "Show me revenue trends by product category this quarter"
- **Operational Analytics**: "Find all API errors in the last 24 hours by service"
- **Customer Intelligence**: "Segment our users by value and identify top spenders"
- **Log Analysis**: "Analyze response times and identify performance bottlenecks"

## Installation

### Prerequisites

- Python 3.11 or higher
- AWS credentials configured
- [super](https://github.com/brimdata/super) binary installed
- Access to S3 buckets containing your data

### Install super Library

**macOS:**
```bash
brew install brimdata/tap/super
```

**Linux:**
```bash
cd /tmp
wget https://github.com/brimdata/super/releases/latest/download/super-linux-amd64.tar.gz
tar -xzf super-linux-amd64.tar.gz
sudo mv super-linux-amd64/super /usr/local/bin/
sudo chmod +x /usr/local/bin/super
```

**Windows:**
Download from [super releases](https://github.com/brimdata/super/releases) and add to PATH.

### Install MCP Server

```bash
# Clone the repository
git clone https://github.com/your-org/s3-super-mcp-server.git
cd s3-super-mcp-server

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import src.mcp_server; print('✅ Installation successful')"
```

## Configuration

### AWS Credentials

Configure AWS credentials using one of these methods:

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment Variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Option 3: IAM Roles (recommended for production)
# Use IAM roles with appropriate S3 permissions
```

### Required S3 Permissions

Your AWS credentials need these S3 permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:ListObjects",
        "s3:ListObjectsV2"
      ],
      "Resource": [
        "arn:aws:s3:::your-data-bucket",
        "arn:aws:s3:::your-data-bucket/*"
      ]
    }
  ]
}
```

### MCP Client Configuration

#### Claude Desktop

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "s3-super-mcp": {
      "command": "python",
      "args": ["/path/to/s3-super-mcp-server/src/mcp_server.py"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

#### Other MCP Clients

The server implements standard MCP protocol and works with any compliant client. Run locally:

```bash
python src/mcp_server.py
```

## Usage

### Basic Queries

Once configured with your MCP client, you can ask natural language questions:

**Revenue Analysis:**
> "Show me the top 10 products by revenue in the last 30 days"

**Customer Segmentation:**
> "Segment our customers by total spend and show average order values"

**Log Analysis:**
> "Find all errors in API logs from yesterday grouped by service"

**Performance Monitoring:**
> "What's the average response time by endpoint over the last week?"

### Available Tools

The MCP server provides these tools for AI assistants:

#### 1. `smart_query`
Primary interface for natural language queries
- Converts business questions to SuperSQL
- Executes queries against S3 data
- Returns formatted results

#### 2. `explore_data`  
Data discovery and schema analysis
- Analyzes data structure and types
- Provides field statistics
- Suggests query patterns

#### 3. `business_metrics`
Pre-built business intelligence calculations
- Revenue analysis
- Customer lifetime value
- Churn analysis  
- Conversion funnels
- Cohort analysis

#### 4. `cross_dataset_join`
Multi-source data analysis
- Join data across S3 locations
- Combine different data formats
- Unified analysis across datasets

#### 5. `data_quality_check`
Data validation and profiling
- Completeness assessment
- Consistency validation
- Quality scoring

### Example Data Structures

The server works best with structured data in S3:

**E-commerce Transactions** (`s3://your-bucket/transactions/*.json`):
```json
{
  "transaction_id": "txn_12345",
  "user_id": "user_789",
  "product": "laptop",
  "amount": 1299.99,
  "timestamp": "2024-01-15T10:30:00Z",
  "channel": "web"
}
```

**Application Logs** (`s3://your-bucket/logs/*.json`):
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "ERROR",
  "service": "api-gateway", 
  "message": "Connection timeout",
  "response_time_ms": 5000
}
```

## Deployment

### Local Development

```bash
# Run the MCP server locally
python src/mcp_server.py

# Run tests
pytest tests/ -v

# Check code quality
black src/ tests/
ruff check src/ tests/
```

### AWS Lambda Deployment

Deploy to AWS Lambda for production use:

```bash
# Build and deploy with SAM
sam build
sam deploy --guided

# Or use the deployment script
./scripts/deploy.sh production
```

The Lambda deployment provides:
- Automatic scaling based on demand
- Built-in monitoring and logging
- Cost-effective pay-per-query pricing
- High availability across regions

### Environment Variables

Configure the server with these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for S3 access | `us-east-1` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `SUPER_BINARY_PATH` | Path to super binary | `/usr/local/bin/super` |
| `QUERY_TIMEOUT` | Query timeout in seconds | `300` |
| `MAX_RESULTS` | Maximum results per query | `10000` |

## Performance Tips

### Query Optimization
- Use specific S3 paths to reduce data scanning
- Apply filters early in queries to minimize processing
- Consider converting JSON to Parquet for better performance

### Data Organization
- Partition S3 data by date/region for faster queries
- Use consistent field naming across datasets
- Store frequently queried data in optimized formats

### Cost Management
- Monitor S3 data transfer costs
- Use S3 Intelligent Tiering for cost optimization
- Set appropriate query timeouts to prevent runaway costs

## Troubleshooting

### Common Issues

**Super binary not found:**
```bash
# Verify installation
which super
super --version

# If not found, reinstall following installation instructions
```

**AWS permissions error:**
```bash
# Test S3 access
aws s3 ls s3://your-bucket/

# Verify credentials
aws sts get-caller-identity
```

**Query timeout:**
- Reduce dataset size with more specific S3 paths
- Use sampling for exploratory queries
- Increase timeout for complex analytics

**Memory issues:**
- Use streaming queries with LIMIT clauses
- Process data in smaller chunks
- Consider upgrading Lambda memory allocation

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
export LOG_LEVEL=DEBUG
python src/mcp_server.py
```

## Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# Format code
black src/ tests/
isort src/ tests/

# Lint code  
ruff check src/ tests/
mypy src/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [GitHub Wiki](https://github.com/your-org/s3-super-mcp-server/wiki)
- **Issues**: [GitHub Issues](https://github.com/your-org/s3-super-mcp-server/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/s3-super-mcp-server/discussions)

## Related Projects

- [super](https://github.com/brimdata/super) - The analytics engine powering this server
- [Model Context Protocol](https://modelcontextprotocol.io/) - The standard protocol for AI tool integration
- [Claude Desktop](https://claude.ai/desktop) - AI assistant with MCP support

---

Built with ❤️ for the data community. Enable your AI assistant to unlock insights from your S3 data lakes.