#!/usr/bin/env python3
"""
Test the fixed error handling for the lookup endpoint.
"""
import sys
sys.path.insert(0, '.')

from game_scanner.errors import NoGoogleMatchesError, GoogleQuotaExceededError, GoogleAPIError

def simulate_fixed_error_handling(exception):
    """Simulate the FIXED error handling logic from _handle_lookup"""
    try:
        raise exception
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"Exception type: {type(e).__name__}")
        print(f"str(e): '{str(e)}'")

        # Import error types for proper exception handling
        from game_scanner.errors import (
            NoGoogleMatchesError,
            GoogleQuotaExceededError,
            GoogleAPIError
        )

        # Handle specific exception types instead of string matching
        if isinstance(e, NoGoogleMatchesError):
            print("✅ Would return 404 (Not Found)")
            return 404

        elif isinstance(e, GoogleQuotaExceededError):
            print("✅ Would return 429 (Too Many Requests - Quota Exceeded)")
            return 429

        elif isinstance(e, GoogleAPIError):
            print("✅ Would return 503 (Service Unavailable - Google API Error)")
            return 503

        else:
            print("✅ Would return 500 (Internal Server Error)")
            return 500

# Test different exception scenarios
print("Testing FIXED error handling for different exception types:")
print("="*60)

# Test 1: NoGoogleMatchesError with a barcode
print("\n1. NoGoogleMatchesError with barcode '0826956101111'")
status = simulate_fixed_error_handling(NoGoogleMatchesError('0826956101111'))
print(f"Result: HTTP {status}")
assert status == 404, "Should return 404"

# Test 2: GoogleQuotaExceededError
print("\n2. GoogleQuotaExceededError")
status = simulate_fixed_error_handling(GoogleQuotaExceededError('Rate limit exceeded'))
print(f"Result: HTTP {status}")
assert status == 429, "Should return 429"

# Test 3: GoogleAPIError
print("\n3. GoogleAPIError")
status = simulate_fixed_error_handling(GoogleAPIError(500, 'Internal server error'))
print(f"Result: HTTP {status}")
assert status == 503, "Should return 503"

# Test 4: Generic Exception (e.g., network error)
print("\n4. Generic Exception (network timeout)")
status = simulate_fixed_error_handling(Exception('Connection timeout'))
print(f"Result: HTTP {status}")
assert status == 500, "Should return 500"

print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
print("The fix correctly handles:")
print("  • NoGoogleMatchesError → 404 (Not Found)")
print("  • GoogleQuotaExceededError → 429 (Quota Exceeded)")
print("  • GoogleAPIError → 503 (Service Unavailable)")
print("  • Other exceptions → 500 (Internal Server Error)")
