#!/usr/bin/env python3
"""
Script to create Telegram session for 2nd automation
Run this once to authenticate the account
"""

import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient
import os

# Load .env.2nd
load_dotenv('.env.2nd', override=True)

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE = os.getenv('PHONE')
SESSION_NAME = os.getenv('SESSION_NAME', 'telegram_session_2nd.session')

async def create_session():
    """Create and authenticate session"""
    print("="*60)
    print("Creating session for 2nd automation")
    print(f"Phone: {PHONE}")
    print(f"Session: {SESSION_NAME}")
    print("="*60)

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    await client.start(phone=PHONE)

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"\n✓ Successfully authenticated!")
        print(f"  Name: {me.first_name} {me.last_name or ''}")
        print(f"  Phone: {me.phone}")
        print(f"  Username: @{me.username}" if me.username else "")
        print(f"\n✓ Session saved: {SESSION_NAME}")
    else:
        print("\n❌ Authentication failed")

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(create_session())
