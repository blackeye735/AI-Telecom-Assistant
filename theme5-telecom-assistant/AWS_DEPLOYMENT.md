# 🚀 Simple AWS Deployment Guide
## AI-Powered Telecom Knowledge Assistant

**Deployment Strategy:** GitHub → Docker → ECR → AWS App Runner

This guide provides the **simplest possible** deployment for a college project demo.

---

## 📋 Prerequisites

1. **AWS Account** with billing enabled
2. **AWS CLI** installed and configured
3. **Docker** installed (or Podman)
4. **Git** repository ready

---

## 🏗️ Architecture Overview

```
┌─────────────────┐
│   Your Laptop   │
│                 │
│  Build Docker   │
│     Image       │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   Amazon ECR    │  ← Container Registry
│  (Image Store)  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ AWS App Runner  │  ← Managed Service
│                 │
│  • FastAPI:8000 │
│  • Streamlit:8501│
│                 │
│  Public URL ✓   │
└─────────────────┘
```

---

## 📦 Step 1: Prepare Your Project

### 1.1 Files Generated

All required files have been created:

```
theme5-telecom-assistant/
├── Dockerfile              ← Multi-stage Docker build
├── docker-compose.yml      ← Local testing
├── startup.sh              ← Runs FastAPI + Streamlit
├── .env.aws                ← AWS environment variables
└── AWS_DEPLOYMENT.md       ← This file
```

### 1.2 Verify Files

```bash
# Check all files exist
ls -l Dockerfile startup.sh docker-compose.yml .env.aws
```

---

## 🐳 Step 2: Test Locally with Docker

Before deploying to AWS, test locally:

### 2.1 Build and Run Locally

```bash
# Set your OpenRouter API key
export OPENROUTER_API_KEY=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

# Build and run with docker-compose
docker-compose up --build

# Access the application
# Streamlit UI: http://localhost:8501
# FastAPI API: http://localhost:8000/docs
```

### 2.2 Test the Application

```bash
# Test FastAPI health
curl http://localhost:8000/health

# Open Streamlit UI in browser
start http://localhost:8501

# Test a query
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is 5G NR?"}'
```

### 2.3 Stop Local Container

```bash
docker-compose down
```

---

## 🏷️ Step 3: Build and Tag Docker Image

### 3.1 Set Variables

```bash
# AWS Configuration
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO_NAME=telecom-assistant
export IMAGE_TAG=latest

# Print to verify
echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "ECR Repository: $ECR_REPO_NAME"
echo "Region: $AWS_REGION"
```

### 3.2 Build Docker Image

```bash
# Build the image
docker build -t $ECR_REPO_NAME:$IMAGE_TAG .

# Verify image was created
docker images | grep $ECR_REPO_NAME
```

**Expected output:**
```
telecom-assistant   latest   abc123def456   2 minutes ago   1.2GB
```

---

## 📤 Step 4: Push Image to Amazon ECR

### 4.1 Create ECR Repository

```bash
# Create ECR repository (one-time setup)
aws ecr create-repository \
    --repository-name $ECR_REPO_NAME \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true

# Output will show repository URI
# Example: 123456789012.dkr.ecr.us-east-1.amazonaws.com/telecom-assistant
```

### 4.2 Authenticate Docker to ECR

```bash
# Get ECR login password and authenticate
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# You should see: "Login Succeeded"
```

### 4.3 Tag Image for ECR

```bash
# Tag the image with ECR repository URI
docker tag $ECR_REPO_NAME:$IMAGE_TAG \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG

# Verify tag
docker images | grep $ECR_REPO_NAME
```

### 4.4 Push Image to ECR

```bash
# Push image to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG

# This will take 2-5 minutes depending on your internet speed
```

**Expected output:**
```
The push refers to repository [123456789012.dkr.ecr.us-east-1.amazonaws.com/telecom-assistant]
abc123: Pushed
def456: Pushed
latest: digest: sha256:... size: 3241
```

### 4.5 Verify Image in ECR

```bash
# List images in ECR
aws ecr describe-images \
    --repository-name $ECR_REPO_NAME \
    --region $AWS_REGION

# You should see your image with tag "latest"
```

---

## 🌐 Step 5: Deploy to AWS App Runner

**Why App Runner?**
- ✓ Simplest AWS deployment option
- ✓ Automatic HTTPS endpoint
- ✓ No VPC configuration needed
- ✓ Pay only for usage
- ✓ Auto-scaling included (if needed)

### 5.1 Create IAM Role for App Runner

```bash
# Create trust policy file
cat > apprunner-trust-policy.json << 'EOF'
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

# Create IAM role
aws iam create-role \
    --role-name AppRunnerECRAccessRole \
    --assume-role-policy-document file://apprunner-trust-policy.json

# Attach ECR read policy
aws iam attach-role-policy \
    --role-name AppRunnerECRAccessRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess

# Get role ARN (save this)
aws iam get-role --role-name AppRunnerECRAccessRole --query 'Role.Arn' --output text
```

### 5.2 Create App Runner Service

```bash
# Set the role ARN from previous step
export ROLE_ARN=$(aws iam get-role --role-name AppRunnerECRAccessRole --query 'Role.Arn' --output text)

# Create App Runner configuration file
cat > apprunner-config.json << EOF
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
          "OPENROUTER_API_KEY": "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",
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

# Create the App Runner service
aws apprunner create-service --cli-input-json file://apprunner-config.json --region $AWS_REGION
```

### 5.3 Get Service URL

```bash
# Wait for service to be ready (takes 3-5 minutes)
aws apprunner list-services --region $AWS_REGION

# Get service details
aws apprunner describe-service \
    --service-arn $(aws apprunner list-services --region $AWS_REGION --query 'ServiceSummaryList[0].ServiceArn' --output text) \
    --region $AWS_REGION \
    --query 'Service.[ServiceUrl, Status]' \
    --output table
```

**Expected output:**
```
------------------------------------------------------------
|                    DescribeService                       |
+----------------------------------------------------------+
|  https://abc123.us-east-1.awsapprunner.com              |
|  RUNNING                                                 |
+----------------------------------------------------------+
```

### 5.4 Access Your Application

```bash
# Get the service URL
export SERVICE_URL=$(aws apprunner describe-service \
    --service-arn $(aws apprunner list-services --region $AWS_REGION --query 'ServiceSummaryList[0].ServiceArn' --output text) \
    --region $AWS_REGION \
    --query 'Service.ServiceUrl' \
    --output text)

echo "Your application is live at: https://$SERVICE_URL"

# Open in browser
start https://$SERVICE_URL
```

---

## 🎯 Step 6: Verify Deployment

### 6.1 Test Health Endpoint

```bash
curl https://$SERVICE_URL/_stcore/health
```

### 6.2 Test FastAPI Backend

**Note:** App Runner only exposes port 8501 (Streamlit). FastAPI runs internally.
The Streamlit UI will call FastAPI on `localhost:8000` inside the container.

### 6.3 Test Streamlit UI

Open in browser: `https://<your-service-url>.awsapprunner.com`

Try sample queries:
- "What is 5G NR?"
- "Explain network slicing in 5G"
- "What are the frequency bands for 5G?"

---

## 💰 Cost Estimate

**AWS App Runner Pricing (us-east-1):**

- **Compute:** $0.064/vCPU-hour + $0.007/GB-hour
- **1 vCPU + 2 GB = ~$0.078/hour**
- **Monthly (24/7):** ~$57/month
- **College demo (8 hours/day):** ~$19/month

**Tip:** Delete the service when not in use to save costs!

---

## 🔄 Step 7: Update Deployment

When you make code changes:

### 7.1 Rebuild and Push

```bash
# Rebuild image
docker build -t $ECR_REPO_NAME:$IMAGE_TAG .

# Retag for ECR
docker tag $ECR_REPO_NAME:$IMAGE_TAG \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG
```

### 7.2 Trigger Deployment

```bash
# Start new deployment
aws apprunner start-deployment \
    --service-arn $(aws apprunner list-services --region $AWS_REGION --query 'ServiceSummaryList[0].ServiceArn' --output text) \
    --region $AWS_REGION

# Check deployment status
aws apprunner list-operations \
    --service-arn $(aws apprunner list-services --region $AWS_REGION --query 'ServiceSummaryList[0].ServiceArn' --output text) \
    --region $AWS_REGION
```

---

## 🗑️ Step 8: Cleanup (Delete Everything)

### 8.1 Delete App Runner Service

```bash
# Delete App Runner service
aws apprunner delete-service \
    --service-arn $(aws apprunner list-services --region $AWS_REGION --query 'ServiceSummaryList[0].ServiceArn' --output text) \
    --region $AWS_REGION

# Wait for deletion (takes 1-2 minutes)
```

### 8.2 Delete ECR Repository

```bash
# Delete ECR repository (including all images)
aws ecr delete-repository \
    --repository-name $ECR_REPO_NAME \
    --region $AWS_REGION \
    --force
```

### 8.3 Delete IAM Role

```bash
# Detach policy
aws iam detach-role-policy \
    --role-name AppRunnerECRAccessRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess

# Delete role
aws iam delete-role --role-name AppRunnerECRAccessRole
```

**Total cleanup time:** ~3 minutes

---

## 🐛 Troubleshooting

### Issue: "Login Succeeded" but push fails

```bash
# Re-authenticate to ECR
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

### Issue: App Runner service fails to start

```bash
# Check service logs
aws apprunner describe-service \
    --service-arn $(aws apprunner list-services --region $AWS_REGION --query 'ServiceSummaryList[0].ServiceArn' --output text) \
    --region $AWS_REGION \
    --query 'Service.Status'

# View logs in CloudWatch (if enabled)
```

### Issue: Application runs but can't query

- Check environment variables are set correctly
- Verify OpenRouter API key is valid
- Check ChromaDB data exists in container

### Issue: Docker build fails

```bash
# Clean Docker cache and rebuild
docker system prune -a
docker build --no-cache -t $ECR_REPO_NAME:$IMAGE_TAG .
```

---

## 📝 Quick Command Reference

```bash
# Build image
docker build -t telecom-assistant:latest .

# Test locally
docker-compose up

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag telecom-assistant:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/telecom-assistant:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/telecom-assistant:latest

# Deploy to App Runner
aws apprunner create-service --cli-input-json file://apprunner-config.json

# Get service URL
aws apprunner describe-service --service-arn <arn> --query 'Service.ServiceUrl'

# Delete everything
aws apprunner delete-service --service-arn <arn>
aws ecr delete-repository --repository-name telecom-assistant --force
```

---

## ✅ Success Checklist

- [ ] Local Docker test successful
- [ ] Image built and tagged
- [ ] Image pushed to ECR
- [ ] IAM role created
- [ ] App Runner service created
- [ ] Service status = RUNNING
- [ ] Public URL accessible
- [ ] Streamlit UI loads
- [ ] Sample query works
- [ ] Demo video recorded (optional)

---

## 📚 Additional Resources

- **App Runner Docs:** https://docs.aws.amazon.com/apprunner/
- **ECR Docs:** https://docs.aws.amazon.com/ecr/
- **Docker Docs:** https://docs.docker.com/

---

## 🎓 For Your College Presentation

**Deployment Summary:**

1. **Built** OCI-compatible Docker image with FastAPI + Streamlit
2. **Pushed** to Amazon ECR (managed container registry)
3. **Deployed** to AWS App Runner (serverless container platform)
4. **Result:** Public HTTPS endpoint with working AI assistant

**Technologies Used:**
- Container: Docker multi-stage build
- Registry: Amazon ECR
- Compute: AWS App Runner (managed, serverless)
- No infrastructure management required!

**Total Deployment Time:** ~15 minutes  
**Monthly Cost:** ~$20 for demo usage  
**Scalability:** Auto-scales from 1-25 instances (if needed)

---

**🚀 Your application is now live on AWS!**

Share your public URL: `https://<your-service>.awsapprunner.com`
