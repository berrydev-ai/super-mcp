// .devcontainer/devcontainer.json
{
    "name": "S3 Super MCP Server Development",
    "image": "mcr.microsoft.com/devcontainers/python:3.11-bullseye",
    "features": {
        "ghcr.io/devcontainers/features/aws-cli:1": {},
        "ghcr.io/devcontainers/features/docker-in-docker:2": {},
        "ghcr.io/devcontainers/features/github-cli:1": {}
    },
    "customizations": {
        "vscode": {
            "extensions": [
                "ms-python.python",
                "ms-python.black-formatter",
                "ms-python.isort",
                "ms-vscode.vscode-json",
                "redhat.vscode-yaml",
                "amazonwebservices.aws-toolkit-vscode"
            ],
            "settings": {
                "python.defaultInterpreterPath": "/usr/local/bin/python",
                "python.formatting.provider": "black",
                "python.linting.enabled": true,
                "python.linting.pylintEnabled": true,
                "editor.formatOnSave": true,
                "editor.codeActionsOnSave": {
                    "source.organizeImports": true
                }
            }
        }
    },
    "postCreateCommand": "bash .devcontainer/setup.sh",
    "forwardPorts": [8080, 3000],
    "portsAttributes": {
        "8080": {
            "label": "MCP Server (Development)",
            "onAutoForward": "notify"
        }
    },
    "remoteUser": "vscode"
}

---
#!/bin/bash
# .devcontainer/setup.sh
set -e

echo "🚀 Setting up S3 Super MCP Server DEVELOPMENT environment..."
echo "ℹ️  Note: Super is installed here for server development/testing"
echo "ℹ️  In production, super runs on server infrastructure (Lambda/containers)"

# Update system
sudo apt-get update

# Install system dependencies
sudo apt-get install -y curl wget jq make build-essential

# Install Python dependencies
pip install --upgrade pip

# Install core dependencies first
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "⚠️  requirements.txt not found - installing core dependencies"
    pip install fastmcp boto3 pytest
fi

# Install development dependencies
if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt
fi

# Install Super library for SERVER DEVELOPMENT
echo "📦 Installing Super library for server development/testing..."
echo "ℹ️  This simulates the server-side super installation"
cd /tmp
wget -q https://github.com/brimdata/super/releases/latest/download/super-linux-amd64.tar.gz
tar -xzf super-linux-amd64.tar.gz
sudo mv super-linux-amd64/super /usr/local/bin/
sudo chmod +x /usr/local/bin/super
rm -rf super-*

# Verify super installation
echo "✅ Verifying super installation..."
super --version

# Set up development environment variables
echo "🔧 Setting up development environment..."
echo 'export SUPER_BINARY_PATH=/usr/local/bin/super' >> ~/.bashrc
echo 'export AWS_DEFAULT_REGION=us-east-1' >> ~/.bashrc
echo 'export LOG_LEVEL=DEBUG' >> ~/.bashrc

# Install AWS SAM CLI for deployment testing
echo "📦 Installing AWS SAM CLI for deployment..."
curl -L -o sam-cli.zip https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip -q sam-cli.zip -d sam-installation
sudo ./sam-installation/install
rm -rf sam-cli.zip sam-installation

# Verify SAM installation
sam --version

# Create test directory structure if it doesn't exist
mkdir -p tests/fixtures

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Environment configured for MCP SERVER development"
echo "📍 Super binary installed at: /usr/local/bin/super"
echo "🔧 This allows you to:"
echo "   • Develop the MCP server locally"
echo "   • Test SuperSQL query execution"  
echo "   • Run integration tests"
echo "   • Debug server functionality"
echo ""
echo "🚀 Production deployment will install super on server infrastructure"
echo "🔌 MCP clients (Claude Desktop) will connect via protocol only"

---
# Additional file: scripts/validate-server-setup.sh
#!/bin/bash
# Validate that the development environment can simulate server-side execution

echo "🧪 Validating server development setup..."

# Check super binary
if command -v super &> /dev/null; then
    echo "✅ Super binary available: $(which super)"
    echo "   Version: $(super --version)"
else
    echo "❌ Super binary not found - server development will fail"
    exit 1
fi

# Check Python dependencies
echo "🐍 Checking Python environment..."
python3 -c "import fastmcp; print('✅ FastMCP available')" || echo "❌ FastMCP missing"
python3 -c "import boto3; print('✅ Boto3 available')" || echo "❌ Boto3 missing"
python3 -c "import pytest; print('✅ Pytest available')" || echo "❌ Pytest missing"

# Test super execution (simulating server-side)
echo "🔧 Testing super execution (server simulation)..."
echo '{"test": "data", "value": 42}' | super -f json -c 'SELECT * FROM this' - > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Super can execute queries (server-side simulation working)"
else
    echo "❌ Super execution failed - check installation"
    exit 1
fi

# Check AWS configuration
if aws sts get-caller-identity &> /dev/null; then
    echo "✅ AWS credentials configured"
else
    echo "⚠️  AWS credentials not configured - some tests may fail"
fi

echo ""
echo "🎯 Development environment ready for MCP server development!"
echo "💡 Remember: In production, super runs on Lambda/containers, not client machines"