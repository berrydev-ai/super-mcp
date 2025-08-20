#!/bin/bash
# .devcontainer/setup.sh
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up dev container user and permissions...${NC}"

# Create mcpuser if it doesn't exist
if ! id "mcpuser" &>/dev/null; then
    echo -e "${YELLOW}Creating mcpuser...${NC}"
    useradd -m -s /bin/bash -u 1000 mcpuser
else
    echo -e "${GREEN}mcpuser already exists${NC}"
fi

# Add mcpuser to sudo group
echo -e "${YELLOW}Adding mcpuser to sudo group...${NC}"
usermod -aG sudo mcpuser

# Allow mcpuser to use sudo without password
echo -e "${YELLOW}Configuring passwordless sudo for mcpuser...${NC}"
echo "mcpuser ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/mcpuser
chmod 440 /etc/sudoers.d/mcpuser

# Set proper ownership of home directory
echo -e "${YELLOW}Setting up home directory permissions...${NC}"
chown -R mcpuser:mcpuser /home/mcpuser

# Set proper ownership of workspace
echo -e "${YELLOW}Setting up workspace permissions...${NC}"
chown -R mcpuser:mcpuser /app

# Create .aws directory with proper permissions if it doesn't exist
if [ ! -d "/home/mcpuser/.aws" ]; then
    echo -e "${YELLOW}Creating .aws directory...${NC}"
    mkdir -p /home/mcpuser/.aws
    chown mcpuser:mcpuser /home/mcpuser/.aws
    chmod 700 /home/mcpuser/.aws
fi

# Install additional development tools as mcpuser
echo -e "${YELLOW}Installing additional development tools...${NC}"
sudo -u mcpuser bash << 'EOF'
# Install Python development tools
pip install --user --upgrade pip setuptools wheel
pip install --user pytest pytest-cov black isort mypy

# Set up shell aliases
echo "alias ll='ls -alF'" >> /home/mcpuser/.bashrc
echo "alias la='ls -A'" >> /home/mcpuser/.bashrc
echo "alias l='ls -CF'" >> /home/mcpuser/.bashrc
echo "alias ..='cd ..'" >> /home/mcpuser/.bashrc
echo "alias ...='cd ../..'" >> /home/mcpuser/.bashrc
echo "alias vba='.venv/bin/activate'" >> /home/mcpuser/.bashrc
echo "alias pir='pip install -r requirements.txt'" >> /home/mcpuser/.bashrc
echo "alias pird='pip install -r requirements-dev.txt'" >> /home/mcpuser/.bashrc

# Add local bin to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> /home/mcpuser/.bashrc
EOF

echo -e "${GREEN}Dev container setup complete!${NC}"
echo -e "${GREEN}User 'mcpuser' has been created with sudo privileges${NC}"
echo -e "${YELLOW}You can now use 'sudo' commands without a password${NC}"

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
wget -v https://github.com/brimdata/super/releases/latest/download/super-linux-amd64.tar.gz
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