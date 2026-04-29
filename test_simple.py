#!/usr/bin/env python3
import base64
import requests
import orjson

GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Referer": "https://www.ratemyprofessors.com/",
    "Origin": "https://www.ratemyprofessors.com",
}

# The working query format
query = """
query NewSearchTeachersQuery($query: TeacherSearchQuery!, $first: Int!, $after: String) {
  newSearch {
    teachers(query: $query, first: $first, after: $after) {
      pageInfo { hasNextPage endCursor }
      edges {
        cursor
        node {
          id legacyId firstName lastName department
          avgRating numRatings
        }
      }
    }
  }
}
"""

school_id = 758
encoded = base64.b64encode(f"School-{school_id}".encode()).decode()
print(f"Using encoded school ID: {encoded}")

payload = {
    "query": query,
    "variables": {
        "query": {"text": "", "schoolID": encoded},
        "first": 5,
        "after": None
    }
}

print("Sending GraphQL request...")
r = requests.post(GRAPHQL_URL, headers=HEADERS, data=orjson.dumps(payload))
result = r.json()

if "errors" in result:
    print(f"Errors: {result['errors']}")
elif "data" in result:
    teachers = result["data"]["newSearch"]["teachers"]
    print(f"PageInfo: {teachers['pageInfo']}")
    print(f"Found {len(teachers['edges'])} professors:")
    for e in teachers["edges"]:
        node = e["node"]
        print(f"  - {node['firstName']} {node['lastName']} (ID: {node['id']}, Rating: {node.get('avgRating')})")
else:
    print(f"Unexpected response: {result}")