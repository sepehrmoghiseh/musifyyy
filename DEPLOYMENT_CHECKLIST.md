# ✅ Deployment Checklist - Fix Render Sleep

## Pre-Deployment Verification

- [x] Added Flask to requirements.txt
- [x] Created health check endpoint at `/`
- [x] Modified app.py to run Flask web server
- [x] Procfile exists and points to app.py
- [x] Created test script (test_health_check.py)
- [x] Created documentation (HEALTH_CHECK_SETUP.md)

## Deployment Steps

### Step 1: Commit and Push Changes

```bash
# Navigate to project directory
cd d:\soundcloud_telegram_bo

# Check what changed
git status

# Add all changes
git add .

# Commit with descriptive message
git commit -m "Add health check endpoint to prevent Render sleep - fixes 404 error"

# Push to GitHub
git push origin main
```

### Step 2: Monitor Render Deployment

1. Go to: https://dashboard.render.com/
2. Find your service: `musifyyy`
3. Click on it to view deployment logs
4. Wait for deployment to complete (~3-5 minutes)
5. Look for these success messages:
   ```
   ✅ Application built successfully
   🚀 WEBHOOK MODE
   🌐 Starting Flask web server...
   * Running on all addresses (0.0.0.0)
   * Running on http://0.0.0.0:10000
   ```

### Step 3: Test Health Check Endpoint

**Option A - PowerShell:**
```powershell
Invoke-WebRequest -Uri "https://musifyyy.onrender.com/" | Select-Object StatusCode, Content
```

**Expected Output:**
```
StatusCode: 200
Content: {"bot":"Musifyyy Bot","message":"Bot is running! 🎵","status":"ok","webhook":"active"}
```

**Option B - Python Test Script:**
```powershell
python test_health_check.py
```

**Expected Output:**
```
🎵 Musifyyy Bot - Health Check Tester
============================================================
🔍 Testing health check endpoint: https://musifyyy.onrender.com/
============================================================
✅ Status Code: 200
📦 Response Body:
{'status': 'ok', 'bot': 'Musifyyy Bot', 'message': 'Bot is running! 🎵', 'webhook': 'active'}

🎉 SUCCESS! Health check is working perfectly!
```

**Option C - Browser:**
Open: https://musifyyy.onrender.com/

Should see:
```json
{"status":"ok","bot":"Musifyyy Bot","message":"Bot is running! 🎵","webhook":"active"}
```

### Step 4: Set Up Cron Job at cron-job.org

1. **Go to**: https://cron-job.org/en/

2. **Sign Up / Log In**
   - Use email or social login
   - Verify your email

3. **Click "Create cronjob"**

4. **Fill in the form**:
   - **Title**: `Musifyyy Bot Keep-Alive`
   - **Address (URL)**: `https://musifyyy.onrender.com/`
   - **Schedule**: Choose **"Every 10 minutes"** from presets
     - Or custom: `*/10 * * * *`
   - **Request method**: `GET`
   - **Request timeout**: `30 seconds`

5. **Advanced settings** (optional but recommended):
   - **Execution**: 
     - ✅ Save responses
     - ✅ Only save failed executions
   - **Notifications**:
     - ✅ Notify me on failed execution (after 3 consecutive failures)
   - **Expected response**:
     - Status code: `200`
     - Search term: `"status":"ok"`

6. **Click "Create cronjob"**

7. **Enable the cron job** (toggle switch on)

### Step 5: Verify Cron Job is Working

**After 10-15 minutes, check:**

1. **cron-job.org Dashboard**:
   - Should show successful executions
   - Status: Green checkmarks ✅
   - Response time: ~500-1000ms

2. **Render Logs**:
   ```bash
   # Should see these every 10 minutes:
   INFO:werkzeug:XXX.XXX.XXX.XXX - - [30/Oct/2025 12:34:56] "GET / HTTP/1.1" 200 -
   ```

3. **Test Bot on Telegram**:
   - Send message to @musifyyybot
   - Should respond instantly (no sleep delay)

## Alternative: Set Up UptimeRobot

If you prefer UptimeRobot:

1. **Go to**: https://uptimerobot.com/
2. **Sign up** (free)
3. **Add New Monitor**:
   - Monitor Type: `HTTP(s)`
   - Friendly Name: `Musifyyy Bot`
   - URL: `https://musifyyy.onrender.com/`
   - Monitoring Interval: `Every 5 minutes` (free tier)
   - Alert Contacts: Your email
4. **Create Monitor**

## Troubleshooting Guide

### Problem: Health check returns 404

**Solution:**
```bash
# 1. Check Render deployment completed
# 2. Check app.py was updated:
git log --oneline -1

# 3. Force redeploy on Render:
#    - Go to Render Dashboard
#    - Click "Manual Deploy" → "Deploy latest commit"

# 4. Check environment variables on Render:
#    - Ensure WEBHOOK_BASE_URL is set to: https://musifyyy.onrender.com
```

### Problem: Health check returns 500

**Solution:**
```bash
# Check Render logs for Python errors:
# - Flask import error? → Check requirements.txt deployed
# - Telegram error? → Check BOT_TOKEN is set correctly
# - Webhook error? → Check WEBHOOK_BASE_URL format
```

### Problem: Cron job keeps failing

**Solution:**
1. Test health check manually first
2. Check cron-job.org timeout setting (increase to 60 seconds)
3. Verify URL is exact: `https://musifyyy.onrender.com/` (with trailing slash)
4. Check "Save failed executions" to see error details

### Problem: Bot still goes to sleep

**Solution:**
1. Verify cron job is **enabled** (green toggle)
2. Check execution history shows recent pings
3. Reduce interval to 5 minutes if using UptimeRobot
4. Check Render service is on free tier (750 hours/month limit)

### Problem: ImportError: Flask not found

**Solution:**
```bash
# Check requirements.txt contains Flask:
cat requirements.txt | grep -i flask

# If missing, add it:
echo "flask>=3.0.0" >> requirements.txt
git add requirements.txt
git commit -m "Add Flask to requirements"
git push
```

## Verification Checklist

After completing all steps, verify:

- [ ] Health check endpoint returns 200 OK
- [ ] Health check returns correct JSON with `"status":"ok"`
- [ ] Cron job shows green checkmarks in dashboard
- [ ] Cron job execution history shows successful pings
- [ ] Render logs show `"GET / HTTP/1.1" 200` every 10 minutes
- [ ] Bot responds on Telegram without delay
- [ ] No "waking up" message/delay when testing bot

## Success!

If all checkmarks above are ✅, your bot will now stay awake 24/7! 🎉

The cron job will ping your bot every 10 minutes, preventing Render from putting it to sleep due to inactivity.

## Important Notes

**Free Tier Limits:**
- Render free tier: 750 hours/month
- With 24/7 uptime: 720 hours/month needed
- You have 30 hours buffer

**What Happens at 750 Hours:**
- Service will sleep until next month
- OR upgrade to paid plan ($7/month)

**Monitor Your Usage:**
- Check Render Dashboard → Service → Metrics
- Watch "Hours Used This Month"
- Set up email alerts at 700 hours

---

Need help? Check `HEALTH_CHECK_SETUP.md` for detailed explanations.
