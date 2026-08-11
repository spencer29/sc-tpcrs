#!/usr/bin/env python3
import urllib.request
import json

# Get a real token first by logging in
try:
    print("Testing API endpoints...")
    
    # Test 1: Vendors (should work with or without auth based on endpoint)
    print("\n1. Testing /api/vendors (list vendors):")
    req = urllib.request.Request('http://localhost:8000/api/vendors')
    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode())
        print(f"   Status: {resp.status} - Found {data.get('total', '?')} vendors")
    except urllib.error.HTTPError as e:
        print(f"   ERROR {e.code}: {e.reason}")
    
    # Test 2: Risk dashboard (requires auth)
    print("\n2. Testing /api/risk/dashboard/summary (requires auth):")
    req = urllib.request.Request('http://localhost:8000/api/risk/dashboard/summary')
    try:
        resp = urllib.request.urlopen(req)
        print(f"   Status: {resp.status} - Success")
    except urllib.error.HTTPError as e:
        print(f"   ERROR {e.code}: {e.reason} (EXPECTED - no token)")
    
    # Test 3: Compliance dashboard (requires auth)
    print("\n3. Testing /api/compliance/dashboard (requires auth):")
    req = urllib.request.Request('http://localhost:8000/api/compliance/dashboard')
    try:
        resp = urllib.request.urlopen(req)
        print(f"   Status: {resp.status} - Success")
    except urllib.error.HTTPError as e:
        print(f"   ERROR {e.code}: {e.reason} (EXPECTED - no token)")

except Exception as e:
    print(f"Exception: {e}")
