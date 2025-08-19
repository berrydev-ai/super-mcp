# S3 Super MCP Server - MVP Specification

## Project Objective

Build an MVP Model Context Protocol server using FastMCP that enables LLMs to query S3 data using the super library. The server must convert natural language business questions into SuperSQL queries and return actionable insights.

## Core Requirements

### Technology Stack
- **FastMCP Library**: Python MCP server framework
- **Super Library**: Data query engine for S3 analytics (**SERVER-SIDE ONLY**)
- **AWS Lambda**: Serverless deployment target
- **S3**: Primary data source

### Critical Architecture Requirement
**The super binary MUST be installed on the server infrastructure** (AWS Lambda, Cloudflare Workers, etc.) where the MCP server runs. The MCP client (Claude Desktop) does NOT need super installed locally. 

**Communication Flow**:
```
MCP Client (Claude Desktop) → MCP Protocol → MCP Server (with super binary) → S3 Data
```

### MVP Scope
Focus on essential functionality for initial launch:
1. Natural language to SuperSQL conversion
2. S3 data querying via super library (server-side execution)
3. Basic business analytics
4. Server-side deployment with super binary

## Required MCP Tools

### 1. query_s3_data
**Purpose**: Execute natural language queries against S3 data

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "request": {
      "type": "string", 
      "description": "Natural language business question"
    },
    "s3_path": {
      "type": "string",
      "description": "S3 URL (s3://bucket/path/*)"
    },
    "limit": {
      "type": "integer",
      "default": 100
    }
  },
  "required": ["request", "s3_path"]
}
```

**Example Requests**:
- "Show me top 10 customers by revenue"
- "Count errors by service in the last 24 hours"  
- "What's the average order value by region?"

**Expected Output**: Formatted table or structured data with query results

### 2. explore_s3_data
**Purpose**: Discover data structure for query building

**Input Schema**:
```json
{
  "type": "object", 
  "properties": {
    "s3_path": {
      "type": "string",
      "description": "S3 URL to analyze"
    },
    "sample_size": {
      "type": "integer",
      "default": 100
    }
  },
  "required": ["s3_path"]
}
```

**Expected Output**:
- Field names and data types
- Sample records (first 5-10)
- Data quality summary (nulls, cardinality)

### 3. list_s3_files
**Purpose**: Browse available data sources

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "bucket": {
      "type": "string", 
      "description": "S3 bucket name"
    },
    "prefix": {
      "type": "string",
      "description": "Path prefix filter"
    }
  },
  "required": ["bucket"]
}
```

**Expected Output**: List of S3 objects with sizes and dates

## Natural Language Processing Requirements

### Intent Pattern Recognition
Must recognize these common business query patterns:

1. **Top N Analysis**: "top 10 products by sales"
   - Template: `SELECT {dimension}, sum({metric}) BY {dimension} ORDER BY sum({metric}) DESC LIMIT {n}`

2. **Time Series**: "revenue by month" 
   - Template: `SELECT date_trunc('month', {timestamp}), sum({metric}) BY date_trunc('month', {timestamp})`

3. **Filtering**: "errors from API service"
   - Template: `FROM {source} WHERE {field} = '{value}'`

4. **Aggregation**: "average response time by endpoint"
   - Template: `SELECT {dimension}, avg({metric}) BY {dimension}`

5. **Counting**: "how many users signed up today"
   - Template: `FROM {source} WHERE {timestamp} > '{today}' | SELECT count()`

### Entity Extraction
Must identify from natural language:
- **Metrics**: revenue, count, average, sum, max, min
- **Dimensions**: product, service, region, user, date
- **Filters**: time ranges, specific values, conditions
- **Operations**: group by, order by, limit

## Super Library Integration (Server-Side)

### Server-Side Binary Execution
The super binary runs exclusively on the MCP server infrastructure. The MCP client sends requests via MCP protocol, and the server executes super commands locally.

**Architecture**:
- **MCP Client**: Sends natural language requests over MCP protocol
- **MCP Server**: Receives requests, converts to SuperSQL, executes super binary
- **Super Binary**: Runs on server, queries S3 data directly
- **Response**: Server formats results and returns via MCP protocol

### Command Execution (Server-Side)
Execute super binary on the server with proper error handling:
```bash
super -f json -c "{query}" {s3_path}
```

**Server Requirements**:
- Super binary must be executable at runtime
- Binary must have S3 access permissions
- Server must handle super process lifecycle

### Supported Data Formats
- JSON (primary)
- CSV  
- Parquet
- JSONL/NDJSON

### Error Handling Requirements
- Super binary not found
- S3 access denied
- Query syntax errors
- Timeout handling (5 minute max)
- Memory limitations

## Server Deployment Options

### AWS Lambda (Primary)
Super binary deployed via Lambda Layer as described above.

### Alternative Server Platforms
**All server platforms must have super binary available at runtime:**

**Docker/Container Deployment**:
```dockerfile
FROM python:3.11-slim
# Install super binary during image build
RUN wget https://github.com/brimdata/super/releases/latest/download/super-linux-amd64.tar.gz && \
    tar -xzf super-linux-amd64.tar.gz && \
    mv super-linux-amd64/super /usr/local/bin/ && \
    chmod +x /usr/local/bin/super
```

**Cloudflare Workers** (if supported):
- Binary would need to be bundled or available in runtime
- May require WebAssembly version of super

**Server Requirements** (All Platforms):
- Super binary executable at known path
- S3 network access for data querying
- Sufficient memory for data processing
- Process execution capabilities

### Client-Side Requirements
**MCP clients (Claude Desktop) only need**:
- MCP protocol support
- Network access to MCP server
- **NO super binary installation required**

### Function Configuration
- **Runtime**: Python 3.11
- **Memory**: 1024MB minimum
- **Timeout**: 300 seconds
- **Architecture**: x86_64
- **Super Binary**: Installed via Lambda Layer

### Required Environment Variables
```
SUPER_BINARY_PATH=/opt/bin/super
AWS_REGION=us-east-1
LOG_LEVEL=INFO
```

### Lambda Layer Requirements (Critical for MVP)
**Super Binary Layer** - Contains the super executable:
- Super binary downloaded during layer build
- Placed at `/opt/bin/super` in Lambda runtime
- Made executable with proper permissions (`chmod +x`)
- Layer attached to Lambda function

**Layer Build Process**:
```bash
# Download super binary for Linux x86_64
wget https://github.com/brimdata/super/releases/latest/download/super-linux-amd64.tar.gz
tar -xzf super-linux-amd64.tar.gz
mkdir -p layer/bin
mv super-linux-amd64/super layer/bin/
chmod +x layer/bin/super
```

### Server-Side Validation
The MCP server must verify super binary availability on startup:
- Check if `/opt/bin/super` exists
- Verify binary is executable
- Test with `super --version`
- Fail fast if super is not available

### IAM Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow", 
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:ListObjects"
      ],
      "Resource": "*"
    }
  ]
}
```

## FastMCP Server Structure

### Required Components

**Main Server Class**:
- Initialize FastMCP server
- Register MCP tools
- Handle stdio communication
- Lambda handler for serverless deployment

**Query Processor**:
- Parse natural language requests
- Extract business entities (metrics, dimensions, filters)  
- Convert to SuperSQL syntax
- Validate and optimize queries

**Super Executor**:
- Execute super binary commands
- Parse JSON results
- Handle errors and timeouts
- Format output for MCP responses

**S3 Helper**:
- List S3 objects
- Validate S3 paths
- Handle AWS credentials

## Business Use Cases (MVP)

### E-commerce Analytics
- Revenue analysis by product/time
- Customer segmentation by spend
- Order frequency and trends

### Log Analysis  
- Error rates by service
- Response time monitoring
- Traffic patterns

### User Behavior
- Signup/conversion funnels
- Feature usage analysis
- Retention metrics

## Test Requirements

### Unit Tests
- Natural language parsing accuracy
- SuperSQL query generation
- Super binary execution
- Error handling

### Integration Tests  
- End-to-end query scenarios
- S3 data access
- Lambda deployment validation
- FastMCP protocol compliance

### Test Data
Create sample S3 datasets:
- E-commerce transactions (JSON)
- Application logs (JSONL)
- User events (CSV)

## Success Criteria

### Functional Requirements
1. Handle 10+ common business query patterns
2. Execute SuperSQL against S3 data successfully
3. Return formatted results within 30 seconds
4. Deploy to AWS Lambda without errors

### Performance Requirements
- Query response time < 30 seconds for 1GB datasets
- Handle concurrent requests (10+)
- Memory usage < 1GB per query

### Quality Requirements
- 90%+ test coverage
- FastMCP protocol compliance
- Comprehensive error handling
- Production-ready logging

## File Structure (Server-Side)

```
src/
├── __init__.py
├── server.py              # FastMCP server and Lambda handler
├── query_processor.py     # Natural language to SuperSQL
├── super_executor.py      # Super binary interface (server-side)
└── s3_helper.py          # S3 operations

tests/
├── test_server.py
├── test_query_processor.py  
├── test_super_executor.py
└── test_integration.py

layers/super/               # Lambda layer with super binary
├── Makefile               # Build super binary layer
└── bin/super              # Super executable (created during build)

template.yaml              # SAM deployment template
requirements.txt           # Python dependencies
pyproject.toml             # Project configuration
```

### Server Initialization Requirements
The server must validate super binary availability on startup:

```python
# Example validation (not implementation)
def validate_super_binary():
    super_path = os.environ.get('SUPER_BINARY_PATH', '/usr/local/bin/super')
    if not os.path.exists(super_path):
        raise RuntimeError(f"Super binary not found at {super_path}")
    if not os.access(super_path, os.X_OK):
        raise RuntimeError(f"Super binary not executable at {super_path}")
```

## Dependencies

### Core Dependencies
```
fastmcp>=0.1.0
boto3>=1.34.0
```

### Development Dependencies  
```
pytest>=7.4.0
pytest-asyncio>=0.21.0
moto>=4.2.0
```

## Deployment Configuration

### SAM Template Requirements (Server-Side Deployment)
- Lambda function with FastMCP handler
- **Super binary layer with executable at /opt/bin/super**
- Function URL for HTTP access (MCP client connectivity)
- IAM role with S3 permissions
- CloudWatch logging

**Critical Layer Configuration**:
```yaml
SuperBinaryLayer:
  Type: AWS::Serverless::LayerVersion
  Properties:
    ContentUri: layers/super/
    CompatibleRuntimes: [python3.11]
  Metadata:
    BuildMethod: makefile
```

### Environment-Specific Configuration
- **Development**: Local server with super binary installed
- **Production**: Lambda deployment with super binary layer

### MCP Client Connection
Clients connect to the deployed server via:
- **Local Development**: stdio connection
- **Production**: HTTP connection to Lambda Function URL
- **No client-side super binary required**

This MVP specification focuses on core functionality needed for initial launch. Additional features like advanced business metrics, multi-dataset joins, and real-time monitoring can be added in future iterations.