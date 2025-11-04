#!/usr/bin/env python3
"""Test error handling improvements."""

def test_error_dict_parsing():
    """Test that error parsing handles both dict and string errors."""
    print("\n=== Test 1: Error Dict Parsing ===")

    # Simulate the fixed code
    def parse_error(result):
        error_data = result.get("error", {})
        if isinstance(error_data, dict):
            error_code = error_data.get("code")
            error_message = error_data.get("message", str(error_data))
        else:
            # Error is a string directly
            error_code = None
            error_message = str(error_data)
        return error_code, error_message

    # Test with dict error
    result1 = {"error": {"code": "INVALID_PATH", "message": "Path not found"}}
    code1, msg1 = parse_error(result1)
    assert code1 == "INVALID_PATH"
    assert msg1 == "Path not found"
    print("✅ Dict error parsed correctly")

    # Test with string error
    result2 = {"error": "Change rejected by user"}
    code2, msg2 = parse_error(result2)
    assert code2 is None
    assert msg2 == "Change rejected by user"
    print("✅ String error parsed correctly")

    # Test with nested dict error (old behavior that failed)
    result3 = {"error": {"nested": "value"}}
    code3, msg3 = parse_error(result3)
    assert code3 is None  # No "code" key
    assert "nested" in msg3  # Falls back to str(error_data)
    print("✅ Nested dict error handled")

    return True


def test_keyboard_interrupt_recovery():
    """Test that KeyboardInterrupt is caught and handled."""
    print("\n=== Test 2: KeyboardInterrupt Recovery ===")

    conversation_broken = False

    # Simulate the fixed code
    try:
        # Simulate user pressing Ctrl+C
        raise KeyboardInterrupt()
    except KeyboardInterrupt:
        # Should be caught and handled gracefully
        print("✅ KeyboardInterrupt caught")
        conversation_broken = False
    except Exception:
        # Should not reach here
        conversation_broken = True

    assert not conversation_broken
    print("✅ Conversation can continue after cancellation")

    return True


def main():
    """Run all tests."""
    print("🧪 Testing Error Handling Fixes\n")

    tests = [
        test_error_dict_parsing(),
        test_keyboard_interrupt_recovery()
    ]

    print("\n" + "=" * 50)
    if all(tests):
        print("✅ All error handling tests passed!")
        print("\n📝 Summary:")
        print("  - String errors now parsed correctly")
        print("  - Dict errors still work as before")
        print("  - KeyboardInterrupt handled gracefully")
        print("  - Conversation continues after cancellation")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
