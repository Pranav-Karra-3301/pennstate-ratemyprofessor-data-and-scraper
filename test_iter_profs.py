#!/usr/bin/env python3
import sys
import time

print("Starting test script", file=sys.stderr)
time.sleep(0.1)

from main import iter_professors

print("Imported iter_professors", file=sys.stderr)
time.sleep(0.1)

try:
    print("Calling iter_professors...", file=sys.stderr)
    profs = list(iter_professors(758, query="", page_size=2))
    print(f"Success! Found {len(profs)} professors", file=sys.stderr)
    for p in profs:
        print(f"  - {p.get('firstName')} {p.get('lastName')}", file=sys.stderr)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()