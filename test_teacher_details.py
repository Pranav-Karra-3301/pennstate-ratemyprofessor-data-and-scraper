#!/usr/bin/env python3
import base64
import requests
import orjson
import json

GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Referer": "https://www.ratemyprofessors.com/",
    "Origin": "https://www.ratemyprofessors.com",
}

# Test fetching teacher details with corrected field names
query = """
query TeacherRatingsQuery($id: ID!, $first: Int!, $after: String) {
  node(id: $id) {
    ... on Teacher {
      id legacyId firstName lastName department
      school { id legacyId name city state }
      avgRating numRatings avgDifficulty wouldTakeAgainPercent
      ratingsDistribution { total r1 r2 r3 r4 r5 }
      courseCodes { courseName courseCount }
      ratings(first: $first, after: $after) {
        pageInfo { hasNextPage endCursor }
        edges {
          cursor
          node {
            id legacyId
            class
            comment
            date
            qualityRating
            difficultyRating
            wouldTakeAgain
            grade
            helpfulRating
            clarityRating
            isForOnlineClass
            attendanceMandatory
            textbookUse
          }
        }
      }
    }
  }
}
"""

# Use a teacher ID from our previous test
teacher_id = "VGVhY2hlci0xMDkzMzM1"  # James Brannick

payload = {
    "query": query,
    "variables": {
        "id": teacher_id,
        "first": 2,
        "after": None
    }
}

print(f"Fetching details for teacher ID: {teacher_id}")
r = requests.post(GRAPHQL_URL, headers=HEADERS, data=orjson.dumps(payload))
result = r.json()

if "errors" in result:
    print(f"Errors: {json.dumps(result['errors'], indent=2)}")
elif "data" in result and result["data"].get("node"):
    teacher = result["data"]["node"]
    print(f"\nTeacher: {teacher['firstName']} {teacher['lastName']}")
    print(f"Department: {teacher['department']}")
    print(f"Rating: {teacher['avgRating']}")
    print(f"Number of ratings: {teacher['numRatings']}")
    print(f"Ratings Distribution: {teacher.get('ratingsDistribution')}")
    print(f"Course Codes: {teacher.get('courseCodes', [])[:3]}")  # First 3 courses

    ratings = teacher.get("ratings", {})
    edges = ratings.get("edges", [])
    print(f"\nFound {len(edges)} reviews:")
    for e in edges[:2]:  # Show first 2 reviews
        review = e["node"]
        print(f"  - Class: {review.get('class')}")
        print(f"    Quality: {review.get('qualityRating')}")
        print(f"    Comment: {review.get('comment', '')[:100]}...")
else:
    print(f"Unexpected response: {json.dumps(result, indent=2)}")