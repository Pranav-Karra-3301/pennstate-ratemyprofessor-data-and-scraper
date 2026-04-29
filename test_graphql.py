#!/usr/bin/env python3
import base64
import requests
import json

GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "*/*",
    "Content-Type": "application/json",
    "Referer": "https://www.ratemyprofessors.com/",
    "Origin": "https://www.ratemyprofessors.com",
}

# Test different school ID formats
school_id = 758
test_formats = [
    f"School-{school_id}",
    f"School:{school_id}",
    f"U2Nob29sLTc1OA==",  # Pre-encoded "School-758"
    str(school_id),
]

# Simple test query
test_query = """
query NewSearchTeachersQuery($query: TeacherSearchQuery!, $first: Int!) {
  newSearch {
    teachers(query: $query, first: $first) {
      edges {
        node {
          id
          firstName
          lastName
        }
      }
    }
  }
}
"""

for format_str in test_formats:
    if not format_str.endswith("=="):  # Not already base64
        encoded = base64.b64encode(format_str.encode()).decode()
    else:
        encoded = format_str

    print(f"\nTesting format: {format_str} -> {encoded}")

    payload = {
        "query": test_query,
        "variables": {
            "query": {"text": "", "schoolID": encoded},
            "first": 1
        }
    }

    try:
        r = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=5)
        result = r.json()

        if "errors" in result:
            print(f"  Error: {result['errors'][0]['message']}")
        elif "data" in result:
            teachers = result.get("data", {}).get("newSearch", {}).get("teachers", {})
            edges = teachers.get("edges", [])
            print(f"  Success! Found {len(edges)} professor(s)")
            if edges:
                print(f"  First prof: {edges[0]['node']}")
    except Exception as e:
        print(f"  Exception: {e}")