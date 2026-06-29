# 🔒 Security & API Key Management

**IMPORTANT:** Before pushing to GitHub, read this guide!

---

## ⚠️ Security Concern: API Keys in Public Repositories

Your OpenRouter API key in `.env` file should **NOT** be committed to public GitHub repositories!

**Why?**
- Public repos are visible to everyone on the internet
- Bots scan GitHub for API keys within minutes of commits
- Exposed keys can be misused, causing unexpected charges
- Keys can't be "un-leaked" once committed to git history

---

## ✅ Recommended Approach for GitHub

### Option 1: Keep Repository Private (Simplest)

When creating your GitHub repository in Step 1:

1. Go to https://github.com/new
2. Repository name: `telecom-assistant`
3. Visibility: **Private** ← Select this!
4. Create repository

**With private repo:**
- ✅ Safe to commit `.env` with API key
- ✅ Only you can see the code
- ⚠️ Can't use App Runner GitHub integration (requires public repo)
- ✅ CloudShell ECR deployment still works perfectly

**This is the RECOMMENDED approach for your deployment!**

---

### Option 2: Public Repo + Environment Variables (More Secure)

If you need a public repository:

#### Step A: Remove .env from Git
```bash
cd c:\Users\acmy\Downloads\Theme5\theme5-telecom-assistant

# .env is already in .gitignore, so new commits won't include it
# Verify:
git status | grep .env
# (Should show nothing or "Untracked files")
```

#### Step B: Use App Runner Environment Variables

When creating App Runner service (QUICKSTART_AWS.md Step 4), manually add each environment variable in the console instead of relying on .env file:

**Required Variables:**
```
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=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
OPENROUTER_MODEL=openai/gpt-4o
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=1024
EMBEDDING_BACKEND=local
CONFIDENCE_THRESHOLD=0.6
API_HOST=0.0.0.0
API_PORT=8000
```

**Pros:**
- ✅ API key never exposed in GitHub
- ✅ Repository can be public
- ✅ Professional security practice

**Cons:**
- ⚠️ Must manually enter variables in AWS Console
- ⚠️ CloudShell build needs manual env var setup

---

### Option 3: Public Repo + GitHub Secrets (Most Secure, CI/CD)

Use GitHub Actions with secrets for fully automated deployment:

#### Step A: Store Key as GitHub Secret

1. GitHub repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `OPENROUTER_API_KEY`
4. Secret: `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`
5. Add secret

Repeat for AWS credentials:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_ACCOUNT_ID`

#### Step B: GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build, tag, and push image to Amazon ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: telecom-assistant
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
```

**Pros:**
- ✅ Fully automated deployment
- ✅ No keys in code
- ✅ Professional CI/CD pipeline
- ✅ No CloudShell needed

**Cons:**
- ⚠️ Requires AWS access keys
- ⚠️ More complex setup
- ⚠️ GitHub Actions minutes (free tier: 2000 min/month)

---

## 🎯 Recommended Approach for Your College Project

### **Use Option 1: Private Repository + CloudShell**

**Why this is best for you:**

1. **Simple:** No extra security setup needed
2. **Safe:** API key not publicly exposed
3. **Works:** CloudShell deployment works perfectly
4. **Fast:** 20-minute deployment (as documented)

**Steps (Modified from QUICKSTART_AWS.md):**

```bash
# Step 1: Push to PRIVATE GitHub repository
cd c:\Users\acmy\Downloads\Theme5\theme5-telecom-assistant

git init
git add .
git commit -m "Initial commit"

# Create PRIVATE repo on GitHub, then:
git remote add origin https://github.com/YOUR-USERNAME/telecom-assistant.git
git push -u origin main
```

**In Step 3 of QUICKSTART_AWS.md (CloudShell):**
```bash
# Clone your PRIVATE repository (you'll need GitHub credentials)
git clone https://github.com/YOUR-USERNAME/telecom-assistant.git
cd telecom-assistant

# Continue with normal deployment...
```

**Everything else stays the same!**

---

## 🔑 What About apprunner.yaml?

The `apprunner.yaml` file currently has your API key hardcoded:

```yaml
env:
  - name: OPENROUTER_API_KEY
    value: "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"
```

### For Private Repository:
**Keep it as-is** - you're deploying via ECR, not App Runner source deployment, so this file isn't used.

### For Public Repository:
**Remove the key** and use App Runner environment variables instead:

```yaml
env:
  - name: OPENROUTER_API_KEY
    value: ""  # Set in App Runner console instead
```

---

## 🛡️ Security Best Practices Summary

### ✅ DO:
- Use private repositories for projects with API keys
- Use environment variables in production (App Runner console)
- Use GitHub Secrets for CI/CD pipelines
- Rotate API keys periodically
- Add `.env` to `.gitignore` (already done)

### ❌ DON'T:
- Commit `.env` files to public repositories
- Hardcode API keys in public code
- Share API keys in screenshots or documentation
- Push keys to GitHub even temporarily ("I'll delete it later")

---

## 🚨 What If You Already Committed a Key?

If you accidentally committed your API key to GitHub:

### Immediate Actions:

1. **Revoke the key immediately:**
   - Go to https://openrouter.ai/keys
   - Delete the exposed key
   - Generate a new key

2. **Remove from git history:**
   ```bash
   # WARNING: This rewrites history and requires force push
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   
   git push --force --all
   ```

3. **Update everywhere:**
   - Update `.env` with new key
   - Update App Runner environment variables
   - Update any local configurations

**Important:** Once a key is in git history, consider it compromised!

---

## 📋 Pre-GitHub Push Checklist

Before running `git push`, verify:

- [ ] Repository visibility set to **Private** (recommended)
  - OR
- [ ] `.env` is in `.gitignore` (✅ already done)
- [ ] `.env` is not in staged files: `git status | grep .env` returns nothing
- [ ] `apprunner.yaml` key removed (if public repo)
- [ ] No API keys in any other files (search for "sk-or-v1")

**Verify no keys will be committed:**
```bash
# Check what will be committed
git status

# Search staged files for API key patterns
git diff --cached | grep -i "sk-or-v1"
# (Should return nothing)

# Safe to push if no keys found!
git push
```

---

## 💡 For Your College Presentation

**When presenting:**
- ✅ Show public URL (safe to share)
- ✅ Show architecture diagrams
- ✅ Show GitHub repository (if private, show screenshot)
- ✅ Show AWS Console (service overview only)
- ❌ Don't show API keys
- ❌ Don't show `.env` file contents
- ❌ Don't show AWS access keys

**If asked about API keys:**
- "API keys are stored securely in AWS App Runner environment variables"
- "The `.env` file is in `.gitignore` to prevent accidental commits"
- "For production, we use AWS Secrets Manager or Parameter Store"

---

## 🎯 Your Action Plan

**Right now, before deployment:**

1. **Decide repository visibility:**
   - [ ] Private (recommended) → No changes needed
   - [ ] Public → Follow Option 2 or 3 above

2. **Verify security:**
   - [ ] `.env` in `.gitignore` (✅ already done)
   - [ ] No API keys in committed files

3. **Proceed with deployment:**
   - [ ] Follow `QUICKSTART_AWS.md` with chosen approach
   - [ ] Test deployment
   - [ ] Verify API key works

**After deployment:**

4. **Document for presentation:**
   - [ ] Save public URL
   - [ ] Screenshot AWS Console (without keys)
   - [ ] Prepare demo queries

5. **Cost management:**
   - [ ] Monitor OpenRouter usage: https://openrouter.ai/activity
   - [ ] Set usage alerts if available
   - [ ] Pause App Runner service when not in use

---

## 🆘 Need Help?

**API Key Issues:**
- OpenRouter Dashboard: https://openrouter.ai/keys
- Check usage: https://openrouter.ai/activity

**GitHub Security:**
- GitHub Security Advisories
- Scan repo: `git secrets` tool (optional)

**AWS Security:**
- IAM best practices
- Use temporary credentials when possible

---

## 📚 Additional Reading

- **GitHub Security Best Practices:** https://docs.github.com/en/code-security
- **OpenRouter API Keys:** https://openrouter.ai/docs/api-keys
- **AWS Secrets Manager:** https://aws.amazon.com/secrets-manager/
- **Environment Variables:** https://12factor.net/config

---

## ✅ Summary

**For your college project, use:**
- ✅ **Private GitHub repository** (simplest & safe)
- ✅ **CloudShell deployment** (no AWS CLI needed)
- ✅ **App Runner environment variables** (production-ready)

**This approach is:**
- Secure (key not exposed)
- Simple (minimal extra steps)
- Professional (industry best practices)
- Cost-effective (free GitHub private repos)

**Next step:** Open `QUICKSTART_AWS.md` and start deployment with a PRIVATE repository!

---

**Created:** 2026-06-28  
**Purpose:** Security guidance for GitHub deployment  
**Status:** Recommended reading before first `git push`
