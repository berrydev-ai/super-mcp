# Multi-stage build for S3 Super MCP Server
FROM python:3.11-slim AS builder

# Install build dependencies including Go
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    build-essential \
    golang-go \
    && rm -rf /var/lib/apt/lists/*

# Install Super binary using Go
RUN go install github.com/brimdata/super/cmd/super@main

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Super binary from builder stage
COPY --from=builder /root/go/bin/super /usr/local/bin/super
RUN chmod +x /usr/local/bin/super

# Create non-root user
RUN useradd -m -u 1000 mcpuser && \
    mkdir -p /app && \
    chown -R mcpuser:mcpuser /app

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Switch to non-root user
USER mcpuser

# Set environment variables
ENV SUPER_BINARY_PATH=/usr/local/bin/super
ENV AWS_DEFAULT_REGION=us-east-1
ENV LOG_LEVEL=INFO
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import subprocess; subprocess.run(['/usr/local/bin/super', '--version'], check=True)" || exit 1

# Expose port for MCP server
EXPOSE 8080

# Run the MCP server
CMD ["python", "src/mcp_server.py"]