"""
Helper script to add sessions directly via command line.
Use this to add sessions until the full UI is implemented.
"""
import asyncio
import sys
from database import db
from session_manager import session_manager


async def add_session_interactive():
    """Interactive session addition"""
    print("=== Add New Session ===\n")

    # Get phone number
    phone = input("Enter phone number (e.g., +79507380505): ").strip()
    if not phone.startswith('+'):
        print("❌ Phone number must start with +")
        return

    # Get API credentials
    try:
        api_id = int(input("Enter API ID (from https://my.telegram.org/apps): ").strip())
        api_hash = input("Enter API Hash: ").strip()
    except ValueError:
        print("❌ API ID must be a number")
        return

    print("\n📱 Creating session...")

    # Initialize database
    db.init_db()

    # Add session to database
    session = await session_manager.add_session(phone, api_id, api_hash)
    print(f"✅ Session created with ID: {session.id}")

    # Authorize session
    print("\n📲 Starting authorization process...")
    print("A code will be sent to your Telegram account...")

    result = await session_manager.authorize_session(session.id, phone)

    if result['status'] == 'code_sent':
        print(f"✅ {result['message']}")
        code = input("\nEnter the verification code: ").strip()

        result = await session_manager.authorize_session(session.id, phone, code=code)

        if result['status'] == 'need_password':
            print(f"🔐 {result['message']}")
            password = input("Enter 2FA password: ").strip()

            result = await session_manager.authorize_session(session.id, phone, password=password)

    if result['status'] == 'authorized':
        print(f"\n✅ {result['message']}")
        print(f"✅ Session {session.id} is ready to use!")
    else:
        print(f"\n❌ Authorization failed: {result.get('message', 'Unknown error')}")

    # Try to connect
    print("\n🔌 Connecting session...")
    try:
        success = await session_manager.connect_session(session.id)
        if success:
            print("✅ Session connected successfully!")
        else:
            print("⚠️  Session created but not connected. You may need to authorize it.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")


async def add_bot_interactive():
    """Interactive bot addition"""
    print("=== Add New Bot ===\n")

    # Initialize database
    db.init_db()
    await session_manager.initialize()

    # List available sessions
    sessions = db.get_all_sessions()
    if not sessions:
        print("❌ No sessions found. Add a session first using option 1.")
        return

    print("Available sessions:")
    for idx, session in enumerate(sessions, 1):
        status = "🟢 Connected" if session.id in session_manager.sessions else "🔴 Disconnected"
        print(f"{idx}. {session.phone} - {status}")

    try:
        choice = int(input("\nSelect session number: ").strip())
        if choice < 1 or choice > len(sessions):
            print("❌ Invalid selection")
            return
        selected_session = sessions[choice - 1]
    except ValueError:
        print("❌ Please enter a number")
        return

    # Get bot details
    bot_username = input("Enter bot username (e.g., @apri1l_test_bot): ").strip()
    if not bot_username.startswith('@'):
        bot_username = '@' + bot_username

    print("\nSelect automation mode:")
    print("1. Full Cycle (all 3 steps)")
    print("2. List Only (only first step)")

    try:
        mode_choice = int(input("Enter choice (1 or 2): ").strip())
        mode = 'full_cycle' if mode_choice == 1 else 'list_only'
    except ValueError:
        print("Using default: full_cycle")
        mode = 'full_cycle'

    print(f"\n🤖 Adding bot {bot_username}...")

    try:
        bot = await session_manager.add_bot(selected_session.id, bot_username, mode)
        print(f"✅ Bot added with ID: {bot.id}")
        print(f"   Username: {bot.bot_username}")
        print(f"   Mode: {bot.automation_mode}")
        print(f"\nUse the Control Bot in Telegram to start the automation!")
    except Exception as e:
        print(f"❌ Failed to add bot: {e}")

    await session_manager.shutdown()


async def main():
    """Main menu"""
    print("\n" + "="*50)
    print("Telegram Bot Automation - Session Manager")
    print("="*50 + "\n")

    print("1. Add new session")
    print("2. Add new bot to existing session")
    print("3. Exit")

    choice = input("\nEnter your choice (1-3): ").strip()

    if choice == '1':
        await add_session_interactive()
    elif choice == '2':
        await add_bot_interactive()
    elif choice == '3':
        print("Goodbye!")
        return
    else:
        print("Invalid choice")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
