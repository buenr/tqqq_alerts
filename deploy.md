# Deploying StockAlert to Google Cloud Run

## Prerequisites

1. **Google Cloud CLI** installed and authenticated
2. **Gmail App Password** (generate from Google Account → Security → 2-Step Verification → App passwords)
3. **Project ID**: Your GCP project ID

---

## Step 1: Set Project and Enable APIs

```powershell
gcloud config set project YOUR_PROJECT_ID

gcloud services enable run.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com cloudscheduler.googleapis.com
```

---

## Step 2: Create Secrets in Secret Manager

> ⚠️ **PowerShell Note**: Use separate commands, not multiline with `\`

```powershell
# Create EMAIL_ADDRESS secret
echo -n "your_gmail@gmail.com" | gcloud secrets create EMAIL_ADDRESS --data-file=-

# Create EMAIL_PASSWORD secret (your 16-char app password)
echo -n "xxxx xxxx xxxx xxxx" | gcloud secrets create EMAIL_PASSWORD --data-file=-
```

---

## Step 3: Deploy to Cloud Run (Initial Deploy)

Deploy without secrets first, then add them:

```powershell
gcloud run deploy stockalert --source . --region us-central1 --platform managed --allow-unauthenticated --memory 512Mi --timeout 300
```

---

## Step 4: Grant Secret Access to Cloud Run

Get the project number and grant the default compute service account access to secrets:

```powershell
# Get project number
gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)"
# Returns: YOUR_PROJECT_NUMBER

# Grant secret access (replace YOUR_PROJECT_NUMBER with actual value)
gcloud secrets add-iam-policy-binding EMAIL_ADDRESS --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding EMAIL_PASSWORD --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"
```

---

## Step 5: Update Service with Secrets

```powershell
gcloud run services update stockalert --region us-central1 --update-secrets "EMAIL_ADDRESS=EMAIL_ADDRESS:latest" --update-secrets "EMAIL_PASSWORD=EMAIL_PASSWORD:latest"
```

---

## Step 6: Create Cloud Scheduler Job

Schedule the alert to run at market open (9:30 AM ET), Monday-Friday:

```powershell
gcloud scheduler jobs create http stockalert-daily --location us-central1 --schedule "30 9 * * 1-5" --uri "YOUR_SERVICE_URL/run" --http-method GET --time-zone "America/New_York"
```

> 📝 Replace `YOUR_SERVICE_URL` with your actual service URL from Step 3

---

## Testing

### Health check:
```powershell
curl YOUR_SERVICE_URL/
```

### Trigger alert manually:
```powershell
curl YOUR_SERVICE_URL/run
```

### Trigger scheduler manually:
```powershell
gcloud scheduler jobs run stockalert-daily --location us-central1
```

### View logs:
```powershell
gcloud run services logs read stockalert --region us-central1 --limit 50
```

---

## Troubleshooting

### "Invalid secret spec" error
**Cause**: PowerShell doesn't handle commas in `--set-secrets` well.  
**Fix**: Use `--update-secrets` with separate flags for each secret (see Step 5).

### "unsupported operand type(s)" with yfinance
**Cause**: Python 3.9 has compatibility issues with newer yfinance.  
**Fix**: Use Python 3.11 in Dockerfile (`FROM python:3.11-slim`).

### Secrets not accessible
**Cause**: Cloud Run service account doesn't have permission to read secrets.  
**Fix**: Run the `gcloud secrets add-iam-policy-binding` commands (see Step 4).

### PowerShell multiline commands fail
**Cause**: PowerShell uses backtick (`) not backslash (\) for line continuation.  
**Fix**: Put entire command on one line, or use backticks.

---

## Updating the Service

### Redeploy after code changes:
```powershell
gcloud run deploy stockalert --source . --region us-central1 --platform managed
```

### Update Gmail password:
```powershell
echo -n "new_app_password" | gcloud secrets versions add EMAIL_PASSWORD --data-file=-
```

---

## Current Deployment

| Resource | Value |
|----------|-------|
| Service URL | YOUR_SERVICE_URL |
| Region | us-central1 |
| Schedule | Mon-Fri 9:30 AM ET |
| Project | YOUR_PROJECT_ID |
