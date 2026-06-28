# 🚀 AWS Console Deployment Guide (No CLI Required)

**Simplest deployment path for college projects** - Deploy directly from GitHub using AWS Console UI.

---

## ✅ Prerequisites Checklist

- [ ] AWS Account with IAM permissions
- [ ] Docker installed locally (for local testing)
- [ ] GitHub account
- [ ] OpenRouter API key: `YOUR_OPENROUTER_API_KEY`

---

## 📋 Deployment Flow

```
GitHub Repository → AWS App Runner → Public HTTPS URL
                    (Builds automatically)
```

**Total Time: 15-20 minutes**  
**Cost: ~$0.078/hour (~$19/month for 8hrs/day demo usage)**

---

## 🎯 Step 1: Push Project to GitHub

### 1.1 Create GitHub Repository
1. Go to https://github.com/new
2. Repository name: `telecom-assistant` (or your choice)
3. Visibility: **Public** (required for free App Runner GitHub integration)
4. **DO NOT** initialize with README
5. Click "Create repository"

### 1.2 Push Your Code
```bash
cd c:\Users\acmy\Downloads\Theme5\theme5-telecom-assistant

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Telecom Knowledge Assistant"

# Add GitHub remote (replace YOUR-USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR-USERNAME/telecom-assistant.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**✅ Verify:** Visit your GitHub repository URL - you should see all project files.

---

## 🎯 Step 2: Create IAM Role for App Runner

### 2.1 Navigate to IAM Console
1. Open AWS Console: https://console.aws.amazon.com/
2. Search for **IAM** in the top search bar
3. Click **IAM** from results

### 2.2 Create App Runner Service Role
1. Click **Roles** in left sidebar
2. Click **Create role** button
3. Select trusted entity:
   - **AWS service**
   - Use case: Search and select **App Runner**
   - Select **App Runner - Service**
4. Click **Next**
5. Permissions: Should auto-select `AWSAppRunnerServicePolicyForECRAccess`
6. Click **Next**
7. Role name: `AppRunnerECRAccessRole`
8. Click **Create role**

**✅ Verify:** You should see the new role in your roles list.

---

## 🎯 Step 3: Deploy with AWS App Runner

### 3.1 Navigate to App Runner Console
1. In AWS Console, search for **App Runner**
2. Click **App Runner** from results
3. Select your preferred region (e.g., **us-east-1**)

### 3.2 Create App Runner Service
1. Click **Create service** button

### 3.3 Configure Source (GitHub)
1. **Repository type:** Source code repository
2. Click **Add new** under "Source code repository provider"
3. **Provider:** GitHub
4. Click **Install another** or **Connect to GitHub**
5. Authorize AWS Connector for GitHub
6. Select your repository: `YOUR-USERNAME/telecom-assistant`
7. Branch: `main`
8. **Deployment trigger:** Automatic
9. Click **Next**

### 3.4 Configure Build
1. **Configuration source:** Use a configuration file (for Dockerfile)
2. Click **Next**

Wait! We need to create an `apprunner.yaml` configuration file first.

---

## 🎯 Step 4: Add App Runner Configuration File

### 4.1 Create apprunner.yaml in Project Root
Create this file in your project root directory:

```yaml
version: 1.0
runtime: python311

build:
  commands:
    build:
      - echo "Building Docker image from Dockerfile..."

run:
  runtime-version: "3.11"
  command: "./startup.sh"
  network:
    port: 8501
    env: APP_PORT
  env:
    - name: LLM_PROVIDER
      value: "openrouter"
    - name: OPENROUTER_API_KEY
      value: "YOUR_OPENROUTER_API_KEY"
    - name: OPENROUTER_MODEL
      value: "openai/gpt-4o"
    - name: LLM_TEMPERATURE
      value: "0.1"
    - name: LLM_MAX_TOKENS
      value: "1024"
    - name: EMBEDDING_BACKEND
      value: "local"
    - name: CONFIDENCE_THRESHOLD
      value: "0.6"
    - name: API_HOST
      value: "0.0.0.0"
    - name: API_PORT
      value: "8000"
```

### 4.2 Push Configuration to GitHub
```bash
git add apprunner.yaml
git commit -m "Add App Runner configuration"
git push
```

---

## 🎯 Step 5: Complete App Runner Service Setup

**WAIT!** There's an easier approach - let's use **Docker image** deployment from source instead.

### 5.1 Go Back to App Runner Console
1. If still in service creation, click **Cancel**
2. Click **Create service** again
3. **Repository type:** Container registry
4. **Provider:** Amazon ECR
5. Select **Browse** - but wait, we don't have an image in ECR yet!

---

## ⚡ SIMPLEST PATH: Use AWS CodeBuild + App Runner

Since you don't have AWS CLI, here's the **ABSOLUTE SIMPLEST** approach:

### Option A: App Runner Source Code Deployment

1. Create `apprunner.yaml` (already provided above)
2. In App Runner Console:
   - **Source:** GitHub repository
   - **Build:** Automatically detect Dockerfile
   - **Runtime:** Managed runtime
3. App Runner builds and deploys automatically

### Option B: Manual ECR Push via AWS CloudShell (No Local CLI)

AWS CloudShell provides a browser-based terminal with AWS CLI pre-installed!

---

## 🎯 **RECOMMENDED: CloudShell Deployment** (Easiest without local CLI)

### 6.1 Open AWS CloudShell
1. In AWS Console, click the **terminal icon** (>_) in top-right corner
2. Wait for CloudShell to initialize (~30 seconds)
3. You now have AWS CLI ready to use!

### 6.2 Clone Your GitHub Repository
```bash
# Clone your repo
git clone https://github.com/YOUR-USERNAME/telecom-assistant.git
cd telecom-assistant
```

### 6.3 Build and Push to ECR
```bash
# Set variables
REGION=us-east-1
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO_NAME=telecom-assistant

# Create ECR repository
aws ecr create-repository --repository-name $REPO_NAME --region $REGION || echo "Repository already exists"

# Get ECR login
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build Docker image (THIS MAY TAKE 10-15 MINUTES)
docker build -t $REPO_NAME .

# Tag image
docker tag $REPO_NAME:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest

# Push to ECR
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest
```

**⏱️ Build time: 10-15 minutes** - CloudShell will show progress.

### 6.4 Note Your Image URI
After push completes, copy this value:
```
IMAGE_URI: <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/telecom-assistant:latest
```

Example: `123456789012.dkr.ecr.us-east-1.amazonaws.com/telecom-assistant:latest`

---

## 🎯 Step 7: Create App Runner Service (Console)

### 7.1 Navigate to App Runner
1. Search for **App Runner** in AWS Console
2. Click **Create service**

### 7.2 Configure Source
1. **Repository type:** Container registry
2. **Provider:** Amazon ECR
3. **Container image URI:** Browse and select your image (or paste URI from Step 6.4)
4. **Deployment trigger:** Manual
5. **ECR access role:** Select `AppRunnerECRAccessRole` (created in Step 2)
6. Click **Next**

### 7.3 Configure Service
1. **Service name:** `telecom-assistant`
2. **Virtual CPU:** 1 vCPU
3. **Memory:** 2 GB
4. **Port:** `8501` (Streamlit port)
5. **Environment variables:** Click **Add environment variable** for each:
   ```
   LLM_PROVIDER=openrouter
   OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY
   OPENROUTER_MODEL=your-model-here
   LLM_TEMPERATURE=0.1
   LLM_MAX_TOKENS=1024
   EMBEDDING_BACKEND=local
   CONFIDENCE_THRESHOLD=0.6
   API_HOST=0.0.0.0
   API_PORT=8000
   ```

### 7.4 Configure Health Check
1. **Health check protocol:** HTTP
2. **Health check path:** `/_stcore/health`
3. **Interval:** 30 seconds
4. **Timeout:** 10 seconds
5. **Healthy threshold:** 3
6. **Unhealthy threshold:** 3

### 7.5 Review and Create
1. Review all settings
2. Click **Create & deploy**
3. Wait for deployment (~5-10 minutes)

**Status progression:**
- Operation in progress → Creating → Deploying → Running ✅

---

## 🎯 Step 8: Get Your Public URL

### 8.1 Find Service URL
1. Once status shows **Running**
2. Look for **Default domain** on the service overview page
3. Format: `https://xxxxxxxxxx.us-east-1.awsapprunner.com`

### 8.2 Test Your Application
1. Copy the URL
2. Open in browser
3. You should see the Streamlit UI!

### 8.3 Test a Query
Try asking: **"What is 5G NR?"**

Expected response should include confidence score and detailed telecom information.

---

## ✅ Success Checklist

- [ ] GitHub repository created and code pushed
- [ ] IAM role `AppRunnerECRAccessRole` created
- [ ] Docker image built in CloudShell
- [ ] Image pushed to ECR successfully
- [ ] App Runner service created
- [ ] Service status shows **Running**
- [ ] Public URL accessible in browser
- [ ] Streamlit UI loads correctly
- [ ] Test query returns valid response with confidence score
- [ ] FastAPI backend health check passes (check logs)

---

## 📊 Monitoring and Logs

### View Application Logs
1. In App Runner service page
2. Click **Logs** tab
3. Select log stream:
   - **Service logs:** Application output (FastAPI, Streamlit)
   - **Deployment logs:** Build and deployment progress
   - **System logs:** App Runner infrastructure

### Check Health
```
Service URL: https://YOUR-SERVICE.awsapprunner.com
Health Check: https://YOUR-SERVICE.awsapprunner.com/_stcore/health
```

---

## 💰 Cost Breakdown

**App Runner Pricing (us-east-1):**
- 1 vCPU + 2 GB memory: **$0.078/hour**
- Free tier: First 2,000 build minutes/month

**Usage Scenarios:**
- **24/7 uptime:** ~$56/month
- **8 hrs/day (demo):** ~$19/month
- **2-hour demo:** ~$0.16

**Pro Tip:** Pause the service when not in use to save costs!

---

## 🔄 Update Deployment

### When You Change Code:

**Option 1: Manual Update (Simple)**
1. Push changes to GitHub
2. Build new image in CloudShell (repeat Step 6.3)
3. In App Runner Console → Service → Click **Deploy**

**Option 2: Automatic Updates**
1. In App Runner service settings
2. Change **Deployment trigger** to **Automatic**
3. Now pushes to GitHub main branch auto-deploy

---

## 🧹 Cleanup (Delete Everything)

### To Stop Charges:

1. **Delete App Runner Service:**
   - App Runner Console → Select service
   - **Actions** → **Delete service**
   - Type service name to confirm

2. **Delete ECR Repository:**
   - ECR Console → Select `telecom-assistant`
   - **Delete** (this removes all images)

3. **Delete IAM Role:**
   - IAM Console → Roles
   - Search `AppRunnerECRAccessRole`
   - Delete

**Cost after deletion: $0**

---

## 🐛 Troubleshooting

### Issue: CloudShell Docker Build Fails
**Solution:** CloudShell has limited storage (1GB). Use GitHub Actions or AWS CodeBuild instead:

1. Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to AWS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Login to ECR
        run: |
          aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com
      - name: Build and Push
        run: |
          docker build -t telecom-assistant .
          docker tag telecom-assistant:latest ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/telecom-assistant:latest
          docker push ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/telecom-assistant:latest
```

2. Add GitHub Secrets:
   - Settings → Secrets and variables → Actions
   - Add: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ACCOUNT_ID`

### Issue: Service Status "Unhealthy"
**Check:**
1. Logs show FastAPI started successfully
2. Port 8501 is configured (not 8000)
3. Health check path is `/_stcore/health`
4. Increase **Healthy threshold** to 5

### Issue: Out of Memory Error
**Solution:** Increase memory to 3 GB or 4 GB in service settings.

### Issue: OpenRouter API Errors
**Check:**
1. API key is correct in environment variables
2. No extra spaces in API key value
3. OpenRouter account has credits/quota

---

## 📚 For Your College Presentation

### Key Talking Points:

1. **Architecture:** Multi-agent LangGraph system with RAG
2. **Deployment:** Serverless container on AWS App Runner
3. **Cost:** ~$19/month for demo usage (very affordable)
4. **Tech Stack:** Python, FastAPI, Streamlit, ChromaDB, OpenRouter
5. **Features:** Confidence-based validation, human approval, session memory

### Demo Flow:
1. Show GitHub repository
2. Show AWS App Runner Console
3. Open public URL in browser
4. Ask sample telecom questions
5. Show confidence scores and validation

---

## 🎉 Summary

**What You Built:**
- ✅ AI-powered telecom knowledge assistant
- ✅ Multi-agent RAG system with LangGraph
- ✅ Production-ready Docker container
- ✅ Public HTTPS deployment on AWS
- ✅ ~$20/month operational cost

**Deployment Time:** ~20 minutes  
**No AWS CLI Required:** Used CloudShell instead  
**Public Access:** HTTPS URL ready to share

**🎓 Perfect for college project demonstrations!**

---

## 📞 Need Help?

- **AWS Support:** https://console.aws.amazon.com/support
- **App Runner Docs:** https://docs.aws.amazon.com/apprunner/
- **OpenRouter API:** https://openrouter.ai/docs

---

**Created:** 2026-06-28  
**Project:** Theme5 Telecom Knowledge Assistant  
**Deployment Target:** AWS App Runner (Serverless Container Platform)
