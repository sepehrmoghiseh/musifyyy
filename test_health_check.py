"""
Test script to verify health check endpoint works correctly.
Run this after deploying to Render to ensure the bot stays awake.
"""
import requests
import sys

def test_health_check(url="https://musifyyy-test.onrender.com"):
    """Test the health check endpoint."""
    print(f"🔍 Testing health check endpoint: {url}")
    print("=" * 60)
    
    try:
        response = requests.get(url, timeout=10)
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"📦 Response Body:")
        print(response.json())
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'ok' and data.get('bot') == 'Musifyyy Bot':
                print("\n🎉 SUCCESS! Health check is working perfectly!")
                print("✅ You can now set up cron-job.org to ping this endpoint")
                return True
            else:
                print("\n⚠️  WARNING: Response format unexpected")
                return False
        else:
            print(f"\n❌ ERROR: Expected 200, got {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to the server")
        print("   - Is the bot deployed on Render?")
        print("   - Is the URL correct?")
        return False
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timed out")
        print("   - The service might be waking up from sleep")
        print("   - Try again in 30 seconds")
        return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def test_webhook_endpoint(url="https://musifyyy-test.onrender.com/webhook"):
    """Test that webhook endpoint is accessible (should not return 404)."""
    print(f"\n🔍 Testing webhook endpoint: {url}")
    print("=" * 60)
    
    try:
        # We expect a POST request, so sending GET should return 405 Method Not Allowed
        # But it should NOT return 404 Not Found
        response = requests.get(url, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 404:
            print("❌ ERROR: Webhook endpoint returns 404!")
            print("   - Check that Flask routes are properly configured")
            return False
        elif response.status_code == 405:
            print("✅ GOOD: Webhook endpoint exists (405 = Method Not Allowed)")
            print("   This is expected since webhooks only accept POST requests")
            return True
        else:
            print(f"ℹ️  INFO: Got status {response.status_code}")
            return True
            
    except Exception as e:
        print(f"⚠️  Could not test webhook: {str(e)}")
        return False


if __name__ == "__main__":
    print("🎵 Musifyyy Bot - Health Check Tester")
    print("=" * 60)
    
    # Allow custom URL as command line argument
    url = sys.argv[1] if len(sys.argv) > 1 else "https://musifyyy-test.onrender.com"
    
    # Run tests
    health_ok = test_health_check(url)
    webhook_ok = test_webhook_endpoint(url + "webhook")
    
    print("\n" + "=" * 60)
    if health_ok:
        print("✅ All tests passed! Bot is ready for cron job monitoring")
        print("\nNext steps:")
        print("1. Go to https://cron-job.org/en/")
        print("2. Create a new cron job")
        print(f"3. Set URL to: {url}")
        print("4. Set interval to: Every 10 minutes")
        print("5. Save and enable")
    else:
        print("❌ Tests failed. Please check the errors above and redeploy.")
        sys.exit(1)
