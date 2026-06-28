# 🚀 Quick Start: AWS Deployment (5 Steps)

**Time:** 20 minutes | **Cost:** ~$19/month (demo usage) | **No AWS CLI needed**

---

## Prerequisites
✅ AWS Account  
✅ Docker installed locally  
✅ GitHub account  

---

## Step 1: Push to GitHub (3 minutes)

```bash
cd c:\Users\acmy\Downloads\Theme5\theme5-telecom-assistant

git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR-USERNAME/telecom-assistant.git
git push -u origin main
```

**Replace `YOUR-USERNAME` with your GitHub username**

---

## Step 2: Create IAM Role (2 minutes)

1. Open AWS Console → **IAM**
2. Click **Roles** → **Create role**
3. Select **AWS service** → **App Runner** → **App Runner - Service**
4. Click **Next** (permissions auto-selected)
5. Role name: `AppRunnerECRAccessRole`
6. Click **Create role**

---

## Step 3: Build & Push with CloudShell (12 minutes)

1. AWS Console → Click **terminal icon** (>_) in top-right
2. Wait for CloudShell to load (~30 seconds)
3. Run these commands:

```bash
# Clone your repository
git clone https://github.com/YOUR-USERNAME/telecom-assistant.git
cd telecom-assistant

# Set variables (CHANGE us-east-1 if needed)
#export REGION=us-east-1
export REGION=eu-north-1
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
#export REPO_NAME=telecom-assistant
export REPO_NAME=ai-telecom-assistant

# Create ECR repository
aws ecr create-repository --repository-name $REPO_NAME --region $REGION

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build Docker image (takes 10-12 minutes)
docker build -t $REPO_NAME .

# Tag and push
docker tag $REPO_NAME:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest

# Get your image URI (COPY THIS!)
echo "Image URI: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest"
```

**⏱️ The `docker build` command takes 10-12 minutes - this is normal!**

**📋 Copy the Image URI** that appears at the end - you'll need it in Step 4.

---

## Step 4: Create App Runner Service (3 minutes)

1. AWS Console → Search **App Runner** → **Create service**

2. **Configure Source:**
   - Repository type: **Container registry**
   - Provider: **Amazon ECR**
   - Container image URI: **Paste your Image URI from Step 3**
   - Deployment trigger: **Manual**
   - ECR access role: **AppRunnerECRAccessRole**
   - Click **Next**

3. **Configure Service:**
   - Service name: `telecom-assistant`
   - Virtual CPU: **1 vCPU**
   - Memory: **2 GB**
   - Port: **8501**
   
4. **Add Environment Variables** (click "Add environment variable" 8 times):
   ```
   LLM_PROVIDER = openrouter
   OPENROUTER_API_KEY = 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
   OPENROUTER_MODEL = openai/gpt-4o
   LLM_TEMPERATURE = 0.1
   LLM_MAX_TOKENS = 1024
   EMBEDDING_BACKEND = local
   CONFIDENCE_THRESHOLD = 0.6
   API_PORT = 8000
   ```

5. **Configure Health Check:**
   - Protocol: **HTTP**
   - Path: `/_stcore/health`
   - Interval: **30**
   - Timeout: **10**
   
6. Click **Next** → **Create & deploy**

**Wait for deployment** (~5-10 minutes). Status will change:  
`Creating` → `Deploying` → `Running` ✅

---

## Step 5: Get Public URL & Test (1 minute)

1. Once status shows **Running**
2. Copy **Default domain** (looks like: `https://xxxxxx.us-east-1.awsapprunner.com`)
3. Open in browser → You should see Streamlit UI!
4. Test query: **"What is 5G NR?"**

---

## ✅ Success!

You now have:
- ✅ Public HTTPS URL
- ✅ AI-powered telecom assistant running 24/7
- ✅ Professional cloud deployment for college project

---

## 💰 Cost Management

**Current usage:** ~$0.078/hour

**To save money:**
- Pause service when not demoing (Service → Actions → Pause)
- Resume before presentation (Service → Actions → Resume)

**Monthly costs:**
- 24/7: ~$56/month
- 8 hrs/day: ~$19/month  
- 2-hour demo: ~$0.16

---

## 🔄 Update Your App

When you change code:

```bash
# Push to GitHub
git add .
git commit -m "Update features"
git push

# In CloudShell, rebuild and push
cd telecom-assistant
git pull
docker build -t $REPO_NAME .
docker tag $REPO_NAME:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest

# In App Runner Console
# Service → Click "Deploy" button
```

---

## 🐛 Common Issues

**CloudShell: "No space left on device"**
- CloudShell has 1GB limit
- Solution: Use GitHub Actions (see AWS_CONSOLE_DEPLOYMENT.md)

**Service Status: "Unhealthy"**
- Check Logs tab in App Runner Console
- Verify port is 8501 (not 8000)
- Verify health check path: `/_stcore/health`

**Blank Streamlit page**
- Wait 2-3 minutes after "Running" status
- Check Service Logs for errors
- Verify environment variables are correct

---

## 🧹 Delete Everything (Stop Charges)

```bash
# 1. Delete App Runner Service
AWS Console → App Runner → Select service → Actions → Delete

# 2. Delete ECR Repository  
AWS Console → ECR → Select telecom-assistant → Delete

# 3. Delete IAM Role
AWS Console → IAM → Roles → Search "AppRunner" → Delete
```

**Cost after deletion: $0/month**

---

## 📚 Full Documentation

For detailed explanations, troubleshooting, and architecture diagrams:
- **Complete guide:** `AWS_CONSOLE_DEPLOYMENT.md`
- **Architecture:** `AI_Telecom_Assistant_Production_Report.html`

---

## 🎯 Your Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] IAM role created
- [ ] Docker image built in CloudShell
- [ ] Image pushed to ECR
- [ ] App Runner service created
- [ ] Status shows "Running"
- [ ] Public URL works
- [ ] Test query successful

---

**🎓 Ready for your college presentation!**

**Your Public URL:** `https://________.us-east-1.awsapprunner.com`  
(Fill in after Step 5)
