#!/usr/bin/env python3
"""
Test script to verify all imports work correctly.
"""

import sys

print("Testing imports...")

try:
    print("  - Importing config...", end=" ")
    from config import Config
    print("✓")

    print("  - Importing modules...", end=" ")
    from modules import (
        ButtonCache,
        ButtonInfo,
        MessageData,
        MessageMonitor,
        ButtonAnalyzer,
        StabilizationDetector,
        ClickExecutor,
        StateMachine,
        AutomationState
    )
    print("✓")

    print("  - Importing bot_automation...", end=" ")
    from bot_automation import BotAutomation
    print("✓")

    print("\n=== Testing basic functionality ===\n")

    # Test ButtonCache
    print("Testing ButtonCache...")
    cache = ButtonCache(max_messages=5)
    print(f"  Created cache with max {cache.max_messages} messages ✓")

    # Test ButtonAnalyzer
    print("Testing ButtonAnalyzer...")
    analyzer = ButtonAnalyzer()
    print("  Created analyzer ✓")

    # Test StabilizationDetector
    print("Testing StabilizationDetector...")
    detector = StabilizationDetector(threshold=0.15, strategy='wait')
    print(f"  Created detector with strategy '{detector.strategy}' ✓")

    # Test StateMachine
    print("Testing StateMachine...")
    sm = StateMachine()
    print(f"  Created state machine in state {sm.current_state.name} ✓")

    # Test state transitions
    sm.start_automation(123)
    print(f"  Transitioned to {sm.current_state.name} ✓")
    sm.reset()
    print(f"  Reset to {sm.current_state.name} ✓")

    # Test Config
    print("\nTesting Config...")
    print(f"  Trigger text: '{Config.TRIGGER_TEXT}' ✓")
    print(f"  Stabilization threshold: {Config.STABILIZATION_THRESHOLD * 1000}ms ✓")
    print(f"  Max retries: {Config.MAX_RETRIES} ✓")

    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60 + "\n")

except ImportError as e:
    print(f"\n❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
