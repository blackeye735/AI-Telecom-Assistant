#!/bin/bash
# ============================================
# Automated AWS Deployment Script
# For Telecom Knowledge Assistant
# ============================================

set -e

echo "============================================"
echo "AWS App Runner Deployment Script"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================
# Step 1: Configuration
# ============================================

echo -e "${BLUE}Step 1: Configuration${NC}"
echo "Setting up AWS configuration..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI is not installed${NC}"
    echo "Install from: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed${NC}"
    echo "Install from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Get AWS configuration
export AWS_REGION=${AWS_REGION:-us-east-1}
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}ERROR: Unable to get AWS Account ID${NC}"
    echo "Please run: aws configure"
    exit 1
fi

export ECR_REPO_NAME=telecom-assistant
export IMAGE_TAG=latest

echo -e "${GREEN}✓ AWS Account ID: $AWS_ACCOUNT_ID${NC}"
echo -e "${GREEN}✓ Region: $AWS_REGION${NC}"
echo -e "${GREEN}✓ ECR Repository: $ECR_REPO_NAME${NC}"
echo ""

# ============================================
# Step 2: Build Docker Image
# ============================================

echo -e "${BLUE}Step 2: Building Docker Image${NC}"
echo "This may take 5-10 minutes..."

docker build -t $ECR_REPO_NAME:$IMAGE_TAG .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
else
    echo -e "${RED}ERROR: Docker build failed${NC}"
    exit 1
fi
echo ""

# ============================================
# Step 3: Create ECR Repository
# ============================================

echo -e "${BLUE}Step 3: Creating ECR Repository${NC}"

# Check if repository exists
REPO_EXISTS=$(aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION 2>/dev/null || echo "")

if [ -z "$REPO_EXISTS" ]; then
    echo "Creating new ECR repository..."
    aws ecr create-repository \
        --repository-name $ECR_REPO_NAME \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true
    echo -e "${GREEN}✓ ECR repository created${NC}"
else
    echo -e "${GREEN}✓ ECR repository already exists${NC}"
fi
echo ""

# ============================================
# Step 4: Authenticate to ECR
# ============================================

echo -e "${BLUE}Step 4: Authenticating to ECR${NC}"

aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Authenticated to ECR${NC}"
else
    echo -e "${RED}ERROR: ECR authentication failed${NC}"
    exit 1
fi
echo ""

# ============================================
# Step 5: Tag and Push Image
# ============================================

echo -e "${BLUE}Step 5: Tagging and Pushing Image to ECR${NC}"

# Tag image
docker tag $ECR_REPO_NAME:$IMAGE_TAG \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG

echo "Pushing image to ECR (this may take 3-5 minutes)..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Image pushed to ECR successfully${NC}"
else
    echo -e "${RED}ERROR: Failed to push image to ECR${NC}"
    exit 1
fi
echo ""

# ============================================
# Step 6: Create IAM Role
# ============================================

echo -e "${BLUE}Step 6: Creating IAM Role for App Runner${NC}"

# Check if role exists
ROLE_EXISTS=$(aws iam get-role --role-name AppRunnerECRAccessRole 2>/dev/null || echo "")

if [ -z "$ROLE_EXISTS" ]; then
    echo "Creating IAM role..."

    # Create trust policy
    cat > /tmp/apprunner-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "build.apprunner.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create role
    aws iam create-role \
        --role-name AppRunnerECRAccessRole \
        --assume-role-policy-document file:///tmp/apprunner-trust-policy.json

    # Attach policy
    aws iam attach-role-policy \
        --role-name AppRunnerECRAccessRole \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess

    # Wait for role to be available
    sleep 10

    echo -e "${GREEN}✓ IAM role created${NC}"
else
    echo -e "${GREEN}✓ IAM role already exists${NC}"
fi

export ROLE_ARN=$(aws iam get-role --role-name AppRunnerECRAccessRole --query 'Role.Arn' --output text)
echo "Role ARN: $ROLE_ARN"
echo ""

# ============================================
# Step 7: Deploy to App Runner
# ============================================

echo -e "${BLUE}Step 7: Deploying to AWS App Runner${NC}"

# Prompt for OpenRouter API key
echo -e "${YELLOW}Please enter your OpenRouter API key:${NC}"
read -r OPENROUTER_KEY

if [ -z "$OPENROUTER_KEY" ]; then
    echo -e "${YELLOW}WARNING: No API key provided. Using default from .env${NC}"
    OPENROUTER_KEY="YOUR_OPENROUTER_API_KEY"
fi

# Create App Runner configuration
cat > /tmp/apprunner-config.json << EOF
{
  "ServiceName": "telecom-knowledge-assistant",
  "SourceConfiguration": {
    "ImageRepository": {
      "ImageIdentifier": "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8501",
        "RuntimeEnvironmentVariables": {
          "LLM_PROVIDER": "openrouter",
          "OPENROUTER_API_KEY": "$OPENROUTER_KEY",
          "OPENROUTER_MODEL": "openai/gpt-4o",
          "LLM_TEMPERATURE": "0.1",
          "LLM_MAX_TOKENS": "1024",
          "EMBEDDING_BACKEND": "local",
          "CONFIDENCE_THRESHOLD": "0.6",
          "API_HOST": "0.0.0.0",
          "API_PORT": "8000"
        }
      }
    },
    "AuthenticationConfiguration": {
      "AccessRoleArn": "$ROLE_ARN"
    },
    "AutoDeploymentsEnabled": false
  },
  "InstanceConfiguration": {
    "Cpu": "1 vCPU",
    "Memory": "2 GB"
  },
  "HealthCheckConfiguration": {
    "Protocol": "HTTP",
    "Path": "/_stcore/health",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }
}
EOF

# Check if service already exists
SERVICE_EXISTS=$(aws apprunner list-services --region $AWS_REGION --query 'ServiceSummaryList[?ServiceName==`telecom-knowledge-assistant`].ServiceArn' --output text 2>/dev/null || echo "")

if [ -n "$SERVICE_EXISTS" ]; then
    echo -e "${YELLOW}Service already exists. Updating deployment...${NC}"
    aws apprunner start-deployment --service-arn $SERVICE_EXISTS --region $AWS_REGION
else
    echo "Creating new App Runner service..."
    aws apprunner create-service --cli-input-json file:///tmp/apprunner-config.json --region $AWS_REGION
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ App Runner service created/updated${NC}"
else
    echo -e "${RED}ERROR: Failed to create App Runner service${NC}"
    exit 1
fi
echo ""

# ============================================
# Step 8: Wait for Deployment
# ============================================

echo -e "${BLUE}Step 8: Waiting for Deployment${NC}"
echo "This typically takes 3-5 minutes..."
echo ""

SERVICE_ARN=$(aws apprunner list-services --region $AWS_REGION --query 'ServiceSummaryList[?ServiceName==`telecom-knowledge-assistant`].ServiceArn' --output text)

for i in {1..60}; do
    STATUS=$(aws apprunner describe-service --service-arn $SERVICE_ARN --region $AWS_REGION --query 'Service.Status' --output text)

    if [ "$STATUS" == "RUNNING" ]; then
        echo -e "${GREEN}✓ Service is RUNNING${NC}"
        break
    elif [ "$STATUS" == "OPERATION_IN_PROGRESS" ]; then
        echo -n "."
        sleep 5
    else
        echo -e "${RED}ERROR: Service status is $STATUS${NC}"
        exit 1
    fi
done
echo ""

# ============================================
# Step 9: Get Service URL
# ============================================

echo -e "${BLUE}Step 9: Getting Service URL${NC}"

SERVICE_URL=$(aws apprunner describe-service --service-arn $SERVICE_ARN --region $AWS_REGION --query 'Service.ServiceUrl' --output text)

echo ""
echo "============================================"
echo -e "${GREEN}🎉 DEPLOYMENT SUCCESSFUL!${NC}"
echo "============================================"
echo ""
echo -e "${GREEN}Your application is live at:${NC}"
echo -e "${BLUE}https://$SERVICE_URL${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Open the URL in your browser"
echo "2. Test with sample queries:"
echo "   - What is 5G NR?"
echo "   - Explain network slicing"
echo "3. Share the URL for your demo!"
echo ""
echo -e "${YELLOW}💰 Cost Estimate:${NC}"
echo "~$0.078/hour (~$19/month for 8hrs/day usage)"
echo ""
echo -e "${YELLOW}🗑️ To delete:${NC}"
echo "Run: aws apprunner delete-service --service-arn $SERVICE_ARN --region $AWS_REGION"
echo ""
echo "============================================"

# Save deployment info
cat > deployment-info.txt << EOF
Deployment Information
======================

Service Name: telecom-knowledge-assistant
Service ARN: $SERVICE_ARN
Service URL: https://$SERVICE_URL
Region: $AWS_REGION
ECR Repository: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME
IAM Role: $ROLE_ARN
Deployment Date: $(date)

Quick Commands:
===============

View service:
  aws apprunner describe-service --service-arn $SERVICE_ARN --region $AWS_REGION

Update deployment:
  aws apprunner start-deployment --service-arn $SERVICE_ARN --region $AWS_REGION

Delete service:
  aws apprunner delete-service --service-arn $SERVICE_ARN --region $AWS_REGION

Delete ECR repository:
  aws ecr delete-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION --force

EOF

echo -e "${GREEN}✓ Deployment info saved to: deployment-info.txt${NC}"
echo ""
