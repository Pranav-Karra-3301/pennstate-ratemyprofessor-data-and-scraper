#!/usr/bin/env python3
import sys

print("Starting test script", file=sys.stderr)

from main import iter_professors

print("Imported iter_professors", file=sys.stderr)

try:
    print("Creating iterator...", file=sys.stderr)
    prof_iter = iter_professors(758, query="", page_size=2)
    print(f"Iterator created: {prof_iter}", file=sys.stderr)

    print("Getting first professor...", file=sys.stderr)
    first_prof = next(prof_iter)
    print(f"First prof: {first_prof.get('firstName')} {first_prof.get('lastName')}", file=sys.stderr)

    print("Getting second professor...", file=sys.stderr)
    second_prof = next(prof_iter)
    print(f"Second prof: {second_prof.get('firstName')} {second_prof.get('lastName')}", file=sys.stderr)

except StopIteration:
    print("No more professors", file=sys.stderr)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)