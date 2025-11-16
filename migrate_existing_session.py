"""
Migrate existing session from .env to Control Panel database.
"""
import asyncio
import os
import shutil
from dotenv import load_dotenv
from database import db
from session_manager import session_manager


async def migrate_session():
    """Migrate existing session to new system"""
    # Load .env
    load_dotenv()

    phone = os.getenv('PHONE')
    api_id = int(os.getenv('API_ID'))
    api_hash = os.getenv('API_HASH')
    bot_username = os.getenv('BOT_USERNAME')
    old_session_file = os.getenv('SESSION_NAME', 'telegram_bot_automation') + '.session'

    if not all([phone, api_id, api_hash]):
        print("❌ Missing credentials in .env file")
        return

    print("="*60)
    print("Migrating Existing Session to Control Panel")
    print("="*60)
    print(f"\n📱 Phone: {phone}")
    print(f"🤖 Bot: {bot_username}")
    print(f"📂 Session file: {old_session_file}")

    # Initialize database
    db.init_db()

    # Check if session already exists
    existing = db.get_session_by_phone(phone)
    if existing:
        print(f"\n⚠️  Session already exists in database (ID: {existing.id})")
        response = input("Do you want to use the existing session? (y/n): ").strip().lower()
        if response != 'y':
            print("❌ Migration cancelled")
            return
        session_id = existing.id
    else:
        # Create new session in database
        print("\n📝 Adding session to database...")
        session = db.add_session(
            phone=phone,
            api_id=api_id,
            api_hash=api_hash,
            session_file=f"sessions/session_{phone}.session"
        )
        session_id = session.id
        print(f"✅ Session added with ID: {session_id}")

        # Copy existing session file to new location
        if os.path.exists(old_session_file):
            print(f"\n📂 Copying session file...")
            os.makedirs('sessions', exist_ok=True)
            new_session_file = f"sessions/session_{phone}.session"
            shutil.copy2(old_session_file, new_session_file)
            print(f"✅ Session file copied to: {new_session_file}")
        else:
            print(f"\n⚠️  Old session file not found at: {old_session_file}")
            print("   You may need to authorize the session again")

    # Initialize session manager
    await session_manager.initialize()

    # Check if bot already exists
    bots = db.get_bots_by_session(session_id)
    bot_exists = any(bot.bot_username == bot_username for bot in bots)

    if not bot_exists and bot_username:
        print(f"\n🤖 Adding bot {bot_username}...")
        try:
            bot = db.add_target_bot(
                session_id=session_id,
                bot_username=bot_username,
                automation_mode='full_cycle'
            )
            print(f"✅ Bot added with ID: {bot.id}")
        except Exception as e:
            print(f"❌ Failed to add bot: {e}")
    else:
        print(f"\n✅ Bot {bot_username} already exists")

    # Try to connect session
    if session_id in session_manager.sessions:
        print(f"\n🟢 Session {session_id} is already connected")
    else:
        print(f"\n🔌 Connecting session {session_id}...")
        try:
            success = await session_manager.connect_session(session_id)
            if success:
                print("✅ Session connected successfully!")
            else:
                print("⚠️  Session needs authorization")
        except Exception as e:
            print(f"⚠️  Connection warning: {e}")
            print("   You can authorize it through the Control Bot")

    await session_manager.shutdown()

    print("\n" + "="*60)
    print("✅ Migration Complete!")
    print("="*60)
    print("\nYou can now use the Control Bot in Telegram to:")
    print("  • View session status")
    print("  • Start/stop automation")
    print("  • Switch between modes (Full Cycle / List Only)")
    print("  • View statistics")
    print("\nTo manage your automation, open your Control Bot in Telegram")
    print("and send /start")


if __name__ == '__main__':
    try:
        asyncio.run(migrate_session())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
