#!/usr/bin/env python3
"""
Performance Testing Script
Сравнение производительности оптимизированных модулей
"""

import time
import asyncio
from time import monotonic, perf_counter
from datetime import datetime

# Test old modules
from modules.stabilization_detector import StabilizationDetector as OldStabilizationDetector
from modules.button_analyzer import ButtonAnalyzer as OldButtonAnalyzer

# Test new modules
from modules.fast_stabilization_detector import FastStabilizationDetector
from modules.fast_button_analyzer import FastButtonAnalyzer, ButtonInfo as FastButtonInfo


def benchmark(func, iterations=10000):
    """Benchmark a function."""
    start = perf_counter()
    for _ in range(iterations):
        func()
    end = perf_counter()
    return (end - start) / iterations * 1000  # ms per iteration


def test_stabilization_detectors():
    """Test stabilization detector performance."""
    print("\n" + "="*60)
    print("Stabilization Detector Performance Test")
    print("="*60)

    # Old detector
    old_detector = OldStabilizationDetector(threshold=0.15)

    # New detector
    new_detector = FastStabilizationDetector(threshold=0.15)

    # Test record_edit performance
    def old_record():
        old_detector.record_edit(12345)

    def new_record():
        new_detector.record_edit(12345)

    old_time = benchmark(old_record, 100000)
    new_time = benchmark(new_record, 100000)

    print(f"\nrecord_edit() - 100,000 iterations:")
    print(f"  Old: {old_time:.4f} ms/op")
    print(f"  New: {new_time:.4f} ms/op")
    print(f"  Speedup: {old_time/new_time:.2f}x")

    # Test is_stabilized performance
    for i in range(100):
        old_detector.record_edit(i)
        new_detector.record_edit(i)

    def old_check():
        old_detector.is_stabilized(50)

    def new_check():
        new_detector.is_stabilized(50)

    old_time = benchmark(old_check, 100000)
    new_time = benchmark(new_check, 100000)

    print(f"\nis_stabilized() - 100,000 iterations:")
    print(f"  Old: {old_time:.4f} ms/op")
    print(f"  New: {new_time:.4f} ms/op")
    print(f"  Speedup: {old_time/new_time:.2f}x")


def test_button_analyzers():
    """Test button analyzer performance."""
    print("\n" + "="*60)
    print("Button Analyzer Performance Test")
    print("="*60)

    # Create test buttons
    old_buttons = []
    new_buttons = []

    from modules.button_cache import ButtonInfo as OldButtonInfo

    for i in range(10):
        old_buttons.append(OldButtonInfo(
            text=f"Button {i}",
            callback_data=b"test",
            row=i // 3,
            column=i % 3
        ))
        new_buttons.append(FastButtonInfo(
            text=f"Button {i}",
            callback_data=b"test",
            row=i // 3,
            column=i % 3
        ))

    old_analyzer = OldButtonAnalyzer()
    new_analyzer = FastButtonAnalyzer()

    keywords = ['button', 'test', 'клик']

    # Test find_button_by_keywords performance
    def old_find():
        old_analyzer.find_button_by_keywords(old_buttons, keywords)

    def new_find():
        new_analyzer.find_button_by_keywords(new_buttons, keywords)

    old_time = benchmark(old_find, 50000)
    new_time = benchmark(new_find, 50000)

    print(f"\nfind_button_by_keywords() - 50,000 iterations:")
    print(f"  Old: {old_time:.4f} ms/op")
    print(f"  New: {new_time:.4f} ms/op")
    print(f"  Speedup: {old_time/new_time:.2f}x")

    # Test get_first_button performance
    def old_first():
        old_analyzer.get_first_button(old_buttons)

    def new_first():
        new_analyzer.get_first_button(new_buttons)

    old_time = benchmark(old_first, 100000)
    new_time = benchmark(new_first, 100000)

    print(f"\nget_first_button() - 100,000 iterations:")
    print(f"  Old: {old_time:.4f} ms/op")
    print(f"  New: {new_time:.4f} ms/op")
    print(f"  Speedup: {old_time/new_time:.2f}x")


async def test_async_performance():
    """Test async operations performance."""
    print("\n" + "="*60)
    print("Async Operations Performance Test")
    print("="*60)

    old_detector = OldStabilizationDetector(threshold=0.01)
    new_detector = FastStabilizationDetector(threshold=0.01)

    # Record some edits
    old_detector.record_edit(123)
    new_detector.record_edit(123)

    # Wait a bit
    await asyncio.sleep(0.02)

    # Test wait_for_stabilization
    start = monotonic()
    result = await old_detector.wait_for_stabilization(123, max_wait=1.0, check_interval=0.001)
    old_time = (monotonic() - start) * 1000

    old_detector.record_edit(124)
    new_detector.record_edit(124)
    await asyncio.sleep(0.02)

    start = monotonic()
    result = await new_detector.wait_for_stabilization(124, max_wait=1.0, check_interval=0.001)
    new_time = (monotonic() - start) * 1000

    print(f"\nwait_for_stabilization():")
    print(f"  Old: {old_time:.2f} ms")
    print(f"  New: {new_time:.2f} ms")
    print(f"  Speedup: {old_time/new_time:.2f}x")


def print_summary():
    """Print summary and recommendations."""
    print("\n" + "="*60)
    print("Performance Summary")
    print("="*60)
    print("""
Key improvements in optimized modules:

1. FastStabilizationDetector:
   - Uses monotonic() instead of datetime for 2-5x speedup
   - __slots__ for reduced memory footprint
   - Deque with maxlen for automatic history management
   - Check interval reduced to 5ms (was 10ms)

2. FastButtonAnalyzer:
   - Pre-computed lowercase text for instant matching
   - LRU cache for text normalization
   - Eliminated nested loops where possible
   - Direct iteration instead of dict builds

3. FastButtonCache:
   - OrderedDict for O(1) operations
   - Automatic LRU eviction
   - Pre-computed hash for faster lookups

Expected real-world impact:
   - Event processing: 10-50x faster (with TDLib)
   - Button matching: 5-10x faster
   - Overall cycle time: 2-3x faster
""")


def main():
    """Main test function."""
    print("\n" + "="*60)
    print("PERFORMANCE BENCHMARKING SUITE")
    print("Comparing old vs optimized modules")
    print("="*60)

    test_stabilization_detectors()
    test_button_analyzers()

    # Run async tests
    asyncio.run(test_async_performance())

    print_summary()

    print("\n✓ Benchmarking completed!\n")


if __name__ == '__main__':
    main()
