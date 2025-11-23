#!/usr/bin/env python3
"""
Session Lock Fix Script
Fixes locked SQLite database session issue
"""

import os
import sys
import time
import subprocess


def find_processes_using_session():
    """Find processes that might be using the session file."""
    session_file = "bot_automation_session.session"

    try:
        result = subprocess.run(
            ["lsof", session_file],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"\n⚠️  Processes using {session_file}:")
            print(result.stdout)
            return True
        else:
            print(f"\n✓ No processes are using {session_file}")
            return False
    except FileNotFoundError:
        print("⚠️  'lsof' command not found, skipping process check")
        return False


def remove_session_files():
    """Remove session files."""
    session_files = [
        "bot_automation_session.session",
        "bot_automation_session.session-journal"
    ]

    removed = []
    not_found = []

    for file in session_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                removed.append(file)
                print(f"✓ Removed: {file}")
            except Exception as e:
                print(f"✗ Failed to remove {file}: {e}")
        else:
            not_found.append(file)

    if not_found:
        print(f"\nℹ️  Files not found (already clean): {', '.join(not_found)}")

    return len(removed) > 0


def main():
    print("="*60)
    print("SESSION LOCK FIX")
    print("="*60)

    # Check if any process is using the session
    has_processes = find_processes_using_session()

    if has_processes:
        print("\n⚠️  IMPORTANT: Close any running instances of main.py first!")
        print("   You can use: pkill -f main.py")
        response = input("\nDo you want to continue anyway? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Aborted.")
            sys.exit(0)

    print("\n" + "="*60)
    print("REMOVING SESSION FILES")
    print("="*60)

    # Remove session files
    removed = remove_session_files()

    print("\n" + "="*60)

    if removed:
        print("✓ SESSION FILES REMOVED")
        print("\nNext steps:")
        print("1. Run: python3 main.py")
        print("2. You will need to re-authenticate with Telegram")
        print("3. Enter your phone number and verification code")
    else:
        print("ℹ️  NO SESSION FILES TO REMOVE")
        print("\nThe database might be locked by another process.")
        print("Try:")
        print("1. Check for running Python processes: ps aux | grep python")
        print("2. Kill them if needed: pkill -f main.py")
        print("3. Run this script again")

    print("="*60 + "\n")


if __name__ == "__main__":
    main()
