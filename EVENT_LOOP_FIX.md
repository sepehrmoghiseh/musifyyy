# Event Loop Fix - RuntimeError Solution

## Problem
The bot was throwing this error:
```
RuntimeError('Event loop is closed')
```

This happened because `asyncio.run()` was being called inside the Flask webhook route, which:
1. Creates a new event loop for each request
2. Closes the loop after processing
3. Conflicts with Python's async event loop management

## Root Cause
```python
# ❌ WRONG - Creates/closes event loop on every request
@flask_app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run(telegram_app.process_update(update))  # ← Problem!
    return jsonify({'ok': True}), 200
```

## Solution
Use a **persistent event loop** running in a background thread:

```python
# ✅ CORRECT - Single persistent event loop
# 1. Create event loop once at startup
loop = asyncio.new_event_loop()

# 2. Run it in a separate daemon thread
def run_event_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

event_thread = Thread(target=run_event_loop, daemon=True)
event_thread.start()

# 3. Schedule tasks in the existing loop
@flask_app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    # Use run_coroutine_threadsafe instead of asyncio.run
    asyncio.run_coroutine_threadsafe(
        telegram_app.process_update(update),
        loop
    )
    return jsonify({'ok': True}), 200
```

## What Changed in app.py

### Added Import
```python
from threading import Thread
```

### Modified main() Function

**Before:**
```python
# Initialize and set webhook
async def setup_webhook():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=webhook_url)

asyncio.run(setup_webhook())  # ❌ Creates temporary loop

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run(telegram_app.process_update(update))  # ❌ Creates new loop each time
    return jsonify({'ok': True}), 200
```

**After:**
```python
# Create persistent event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Initialize and set webhook using the persistent loop
async def setup_webhook():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=webhook_url)

loop.run_until_complete(setup_webhook())  # ✅ Uses persistent loop

# Start event loop in background thread
def run_event_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

event_thread = Thread(target=run_event_loop, daemon=True)
event_thread.start()

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    # Schedule in existing loop
    asyncio.run_coroutine_threadsafe(
        telegram_app.process_update(update),
        loop
    )
    return jsonify({'ok': True}), 200
```

## Benefits

1. **✅ Single Event Loop**: One loop for all async operations
2. **✅ Thread-Safe**: `run_coroutine_threadsafe` properly schedules tasks
3. **✅ No Loop Conflicts**: Flask (sync) and Telegram (async) work together
4. **✅ Better Performance**: No loop creation/destruction overhead
5. **✅ Proper Resource Management**: Loop runs continuously, no premature closure

## Testing

After deploying, your bot should:
- ✅ Respond to `/start` and other commands without errors
- ✅ Process webhook updates successfully
- ✅ Show no "Event loop is closed" errors in logs
- ✅ Health check endpoint still works at `https://musifyyy-test.onrender.com/`

## Deploy This Fix

```bash
cd d:\soundcloud_telegram_bo
git add app.py
git commit -m "Fix RuntimeError: Event loop is closed - use persistent event loop with threading"
git push origin test
```

Then check Render logs for:
```
✅ Application built successfully
🚀 WEBHOOK MODE
✅ Webhook set to: https://musifyyy-test.onrender.com/webhook
🔄 Event loop started in background thread
🌐 Starting Flask web server...
```

## Technical Background

### Why asyncio.run() Doesn't Work Here

`asyncio.run()` is designed for simple scripts where you:
1. Run one async main function
2. Exit when done

It does this:
```python
def run(coro):
    loop = asyncio.new_event_loop()  # Create new loop
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()  # Close loop ← This causes problems!
```

In a web server handling multiple requests, you need a **persistent loop** that:
- Stays open between requests
- Can schedule multiple coroutines
- Runs continuously in the background

### Thread Safety

`asyncio.run_coroutine_threadsafe()` is specifically designed for:
- Scheduling coroutines from a different thread (Flask's request handler)
- Thread-safe queue management
- Proper synchronization between sync and async code

## Common Patterns

### ❌ Anti-Pattern (Don't Do This)
```python
# In Flask route
asyncio.run(some_async_function())  # Creates/destroys loop each request
```

### ✅ Best Practice (Do This)
```python
# At startup
loop = asyncio.new_event_loop()
Thread(target=lambda: loop.run_forever(), daemon=True).start()

# In Flask route
asyncio.run_coroutine_threadsafe(some_async_function(), loop)
```

## References

- [asyncio Event Loop](https://docs.python.org/3/library/asyncio-eventloop.html)
- [run_coroutine_threadsafe](https://docs.python.org/3/library/asyncio-task.html#asyncio.run_coroutine_threadsafe)
- [python-telegram-bot Webhooks](https://docs.python-telegram-bot.org/en/stable/examples.webhookbot.html)
