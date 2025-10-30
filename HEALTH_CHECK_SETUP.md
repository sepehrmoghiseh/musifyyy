# Health Check Setup for Render

## Problem
Render puts free-tier services to sleep after 15 minutes of inactivity. This causes your bot to stop responding until a request wakes it up.

## Solution
The bot now includes a health check endpoint at the root URL (`/`) that returns a JSON response. You can ping this endpoint regularly to keep the service awake.

## What Changed

### 1. Added Flask Web Server
- The bot now runs a Flask web server alongside the Telegram webhook
- **Health Check Endpoint**: `GET https://musifyyy.onrender.com/`
  - Returns: `{"status": "ok", "bot": "Musifyyy Bot", "message": "Bot is running! 🎵", "webhook": "active"}`
  - Status Code: `200 OK`

### 2. Updated Requirements
- Added `flask>=3.0.0` to `requirements.txt`

## Setup Cron Job Monitoring

### Using cron-job.org (Free)

1. **Go to**: https://cron-job.org/en/
2. **Create Account** (free)
3. **Create New Cron Job**:
   - **Title**: Musifyyy Bot Keep-Alive
   - **URL**: `https://musifyyy.onrender.com/`
   - **Schedule**: Every 10 minutes (or choose from preset: "Every 10 minutes")
   - **HTTP Method**: GET
   - **Expected Response**: 200 OK

4. **Save and Enable**

### Using UptimeRobot (Alternative)

1. **Go to**: https://uptimerobot.com/
2. **Sign up** (free tier allows 50 monitors)
3. **Add New Monitor**:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: Musifyyy Bot
   - **URL**: `https://musifyyy.onrender.com/`
   - **Monitoring Interval**: Every 5 minutes (free tier)

4. **Create Monitor**

### Using GitHub Actions (Free for public repos)

Create `.github/workflows/keep-alive.yml`:

```yaml
name: Keep Alive

on:
  schedule:
    # Run every 10 minutes
    - cron: '*/10 * * * *'
  workflow_dispatch:

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping health check endpoint
        run: |
          curl -f https://musifyyy.onrender.com/ || exit 1
```

## Deployment Steps

1. **Commit changes**:
   ```bash
   git add .
   git commit -m "Add health check endpoint for Render keep-alive"
   git push
   ```

2. **Render will automatically redeploy** (if connected to GitHub)

3. **Test the health check**:
   ```bash
   curl https://musifyyy.onrender.com/
   ```
   
   Expected response:
   ```json
   {
     "status": "ok",
     "bot": "Musifyyy Bot",
     "message": "Bot is running! 🎵",
     "webhook": "active"
   }
   ```

4. **Set up cron job** using one of the methods above

## Verify It's Working

1. **Check Render Logs**:
   - Go to Render Dashboard → Your Service → Logs
   - Look for: `🌐 Starting Flask web server...`
   - Health check pings will show as: `"GET / HTTP/1.1" 200`

2. **Test Manually**:
   ```bash
   # In PowerShell
   Invoke-WebRequest -Uri "https://musifyyy.onrender.com/" | Select-Object -ExpandProperty Content
   ```

3. **Monitor Bot Responsiveness**:
   - Try your bot on Telegram: @musifyyybot
   - It should respond instantly even after idle periods

## Troubleshooting

### Bot Returns 404
- Make sure you pushed the updated code to GitHub
- Check that Render redeployed successfully
- Verify `WEBHOOK_BASE_URL` is set in Render environment variables

### Health Check Returns 500
- Check Render logs for errors
- Ensure all dependencies installed correctly
- Verify Flask version is compatible

### Cron Job Disabled
- Check cron-job.org account for failed requests
- Verify the URL is correct (no typos)
- Ensure health check endpoint returns 200 status

### Bot Still Sleeping
- Reduce ping interval (try every 5 minutes)
- Check Render activity logs to confirm pings are received
- Consider upgrading to Render paid tier for always-on service

## Notes

- **Free Tier Limitations**: Render free tier has 750 hours/month. With constant pinging, you'll use all hours.
- **Upgrade Option**: Consider Render's $7/month plan for true always-on service.
- **Alternative**: Use Railway, Fly.io, or other platforms with better free tiers.

## Security Note

The health check endpoint is public and doesn't expose sensitive information. It only confirms the service is running.
