#!/usr/bin/env python3
"""
Reproduce the HTTP 500 error issue from the lookup endpoint.
"""
import sys
sys.path.insert(0, '.')

from game_scanner.errors import NoGoogleMatchesError, GoogleQuotaExceededError, GoogleAPIError

def simulate_error_handling(exception):
    """Simulate the error handling logic from _handle_lookup"""
    try:
        raise exception
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"Exception type: {type(e).__name__}")
        print(f"str(e): '{str(e)}'")
        print(f"str(e).lower(): '{str(e).lower()}'")

        # This is the actual error handling logic from main.py line 277
        error_msg = str(e).lower()
        if 'nothing found' in error_msg or 'not found' in error_msg or 'no results' in error_msg:
            print("✅ Would return 404 (Not Found)")
            return 404
        else:
            print("❌ Would return 500 (Server Error)")
            return 500

# Test different exception scenarios
print("Testing error handling for different exception types:")
print("="*60)

# Test 1: NoGoogleMatchesError with a barcode
print("\n1. NoGoogleMatchesError with barcode '0826956101111'")
status = simulate_error_handling(NoGoogleMatchesError('0826956101111'))
print(f"Result: HTTP {status}")

# Test 2: GoogleQuotaExceededError
print("\n2. GoogleQuotaExceededError")
status = simulate_error_handling(GoogleQuotaExceededError('Rate limit exceeded'))
print(f"Result: HTTP {status}")

# Test 3: GoogleAPIError
print("\n3. GoogleAPIError")
status = simulate_error_handling(GoogleAPIError(500, 'Internal server error'))
print(f"Result: HTTP {status}")

# Test 4: Generic Exception (e.g., network error)
print("\n4. Generic Exception (network timeout)")
status = simulate_error_handling(Exception('Connection timeout'))
print(f"Result: HTTP {status}")

print("\n" + "="*60)
print("ANALYSIS:")
print("="*60)
print("❌ NoGoogleMatchesError returns 500 instead of 404")
print("   - str(e) returns the query value, not 'nothing found'")
print("   - The error message is stored in e.message but not returned by str()")
print()
print("❌ GoogleQuotaExceededError returns 500 instead of special handling")
print("   - Should be caught and handled with quota exceeded response")
print()
print("FIX: Check exception TYPE instead of string matching")
