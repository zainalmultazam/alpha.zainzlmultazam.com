import asyncio
import os
import sys

app_root = os.path.dirname(os.path.abspath(__file__))
if app_root not in sys.path:
    sys.path.insert(0, app_root)

from app.services.telegram_bot import telegram_polling_worker, sentinel_scheduler_worker
from app.engine.journal import init_db

async def main():
    init_db()
    print("Starting Alpha Telegram Bot & Safety Sentinel Worker...")
    await asyncio.gather(
        telegram_polling_worker(),
        sentinel_scheduler_worker()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot worker stopped.")
