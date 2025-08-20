#!/bin/bash
# Deploy script for S3 Super MCP Server

set -e

# Configuration
STACK_NAME="s3-super-mcp-server"
REGION=${AWS_REGION:-us-east-1}
STAGE=${1:-dev}

echo "🚀 Deploying S3 Super MCP Server"
echo "   Stack: $STACK_NAME-$STAGE"
echo "   Region: $REGION"
echo "   Stage: $STAGE"
echo

# Validate AWS CLI and credentials
echo "📋 Validating AWS credentials..."
aws sts get-caller-identity > /dev/null || {
    echo "❌ AWS credentials not configured or invalid"
    echo "Please run: aws configure"
    exit 1
}
echo "✅ AWS credentials valid"

# Validate SAM CLI
echo "📋 Validating SAM CLI..."
sam --version > /dev/null || {
    echo "❌ SAM CLI not found"
    echo "Please install SAM CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
}
echo "✅ SAM CLI found"

# Build the application
echo "🔨 Building SAM application..."
sam build --use-container || {
    echo "❌ SAM build failed"
    exit 1
}
echo "✅ Build completed"

# Deploy the application
echo "🚀 Deploying to AWS..."
if [ "$STAGE" = "dev" ]; then
    # Development deployment with guided setup
    sam deploy \
        --stack-name "$STACK_NAME-$STAGE" \
        --region "$REGION" \
        --parameter-overrides Stage="$STAGE" \
        --capabilities CAPABILITY_IAM \
        --resolve-s3 || {
        echo "❌ Deployment failed"
        exit 1
    }
else
    # Production deployment (assumes parameters are configured)
    sam deploy \
        --stack-name "$STACK_NAME-$STAGE" \
        --region "$REGION" \
        --parameter-overrides Stage="$STAGE" \
        --capabilities CAPABILITY_IAM \
        --no-confirm-changeset || {
        echo "❌ Deployment failed"
        exit 1
    }
fi

echo "✅ Deployment completed successfully!"

# Get deployment outputs
echo
echo "📄 Deployment Outputs:"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME-$STAGE" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

echo
echo "🎉 S3 Super MCP Server deployed successfully!"
echo "   Use the Function URL above to connect MCP clients"