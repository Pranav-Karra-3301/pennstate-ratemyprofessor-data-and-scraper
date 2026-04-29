#!/usr/bin/env python3
"""
RMP → JSON scraper for Penn State University (school_id=758)
----------------------------------------------------------------
Goal: pull *meaningful* professor + review data to JSON/JSONL for use in RAG.

Design:
  • Primary path: call RateMyProfessors' public GraphQL endpoint used by the site.
    - Enumerate all professors for a school via paginated search.
    - For each professor, fetch profile details, top tags, course codes, and all reviews (paginated).
  • Fallback (optional): if GraphQL schema changes or is blocked for you,
    use Playwright to click “Show More” and crawl individual profile pages to extract
    core fields (slower/fragile but unblocks you). Disabled by default.

Outputs:
  1) data/professors.jsonl      → one JSON object per professor (no long review text)
  2) data/reviews.jsonl         → one JSON object per *review*, linked by professor_id
  3) data/professors_min.json   → compact JSON list (id, name, dept, rating, counts)

Quickstart
----------
python3 -m venv .venv && source .venv/bin/activate
pip install requests tenacity tqdm orjson
# (Optional fallback) pip install playwright && playwright install chromium

python rmp_psu_scraper.py --school-id 758 --max-profs 0 --reviews yes

Notes
-----
• This script calls the same endpoint your browser uses on ratemyprofessors.com.
• Please review RMP Terms of Use and robots.txt before large-scale scraping.
• Rate limit requests (the script does). Avoid parallel review scraping to be polite.
• If RMP changes GraphQL, see DevTools → Network → filter "graphql" and paste the
  latest operation + fields into the query strings below.
"""
from __future__ import annotations

import argparse
import base64
import os
import time
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

import requests
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from tqdm import tqdm
import orjson

# ---------------------------
# Config
# ---------------------------
GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "*/*",
    "Content-Type": "application/json",
    # RMP often expects a referer. Keep it consistent with your target page.
    "Referer": "https://www.ratemyprofessors.com/search/professors/758?q=*",
    "Origin": "https://www.ratemyprofessors.com",
}

# ---------------------------
# GraphQL Queries (reverse‑engineered from the site; update if schema changes)
# ---------------------------
SEARCH_PROFESSORS_QUERY = """
query NewSearchTeachersQuery($query: TeacherSearchQuery!, $first: Int!, $after: String) {
  newSearch {
    teachers(query: $query, first: $first, after: $after) {
      pageInfo { hasNextPage endCursor }
      edges {
        cursor
        node {
          id legacyId firstName lastName department
          school { id legacyId name city state }
          avgRating numRatings avgDifficulty wouldTakeAgainPercent
        }
      }
    }
  }
}
"""

TEACHER_DETAILS_WITH_RATINGS_QUERY = """
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

# ---------------------------
# Utils
# ---------------------------

def dump_jsonl(path: str, rows: Iterable[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        for row in rows:
            f.write(orjson.dumps(row))
            f.write(b"\n")

def write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(orjson.dumps(obj, option=orjson.OPT_INDENT_2))

@retry(wait=wait_exponential_jitter(initial=1, max=8), stop=stop_after_attempt(5))
def gql(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    payload = {"query": query, "variables": variables}
    r = requests.post(GRAPHQL_URL, headers=HEADERS, data=orjson.dumps(payload), timeout=10)
    r.raise_for_status()
    out = r.json()
    if "errors" in out:
        raise RuntimeError(f"GraphQL errors: {out['errors']}")
    return out["data"]

# ---------------------------
# GraphQL → Enumerate professors
# ---------------------------

def iter_professors(school_id: int, query: str = "", page_size: int = 50) -> Generator[Dict[str, Any], None, None]:
    # RateMyProfessors uses base64-encoded IDs in format "School-{id}"
    encoded_school_id = base64.b64encode(f"School-{school_id}".encode()).decode()
    print(f"DEBUG: iter_professors called with school_id={school_id}, encoded={encoded_school_id}")

    after = None
    max_iterations = 100  # Safety limit to prevent infinite loops
    iteration = 0


    while iteration < max_iterations:
        iteration += 1

        data = gql(
            SEARCH_PROFESSORS_QUERY,
            {"query": {"text": query, "schoolID": encoded_school_id}, "first": page_size, "after": after},
        )


        teachers = (
            data.get("newSearch", {})
            .get("teachers", {})
        )

        edges = teachers.get("edges", [])
        page = teachers.get("pageInfo", {})

        for e in edges:
            node = e.get("node", {})
            if node:
                yield node

        if not page.get("hasNextPage"):
            break
        after = page.get("endCursor")
        if not after:  # Safety check
            break
        time.sleep(0.4)

# ---------------------------
# GraphQL → For each professor, fetch details + all reviews
# ---------------------------

def fetch_prof_details_and_reviews(teacher_id: str, review_page_size: int = 50) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    # Collect details and all paginated review edges
    after = None
    reviews: List[Dict[str, Any]] = []
    details: Optional[Dict[str, Any]] = None

    while True:
        data = gql(
            TEACHER_DETAILS_WITH_RATINGS_QUERY,
            {"id": teacher_id, "first": review_page_size, "after": after},
        )
        node = data.get("node")
        if not node:
            break
        if details is None:
            # Copy scalar/meta fields once
            details = {
                k: node.get(k)
                for k in [
                    "id", "legacyId", "firstName", "lastName", "department",
                    "avgRating", "numRatings", "avgDifficulty", "wouldTakeAgainPercent",
                ]
            }
            school = node.get("school") or {}
            details["school"] = {
                "id": school.get("id"),
                "legacyId": school.get("legacyId"),
                "name": school.get("name"),
                "city": school.get("city"),
                "state": school.get("state"),
            }
            details["ratingsDistribution"] = node.get("ratingsDistribution")
            details["courseCodes"] = [{"name": c.get("courseName"), "count": c.get("courseCount")} for c in (node.get("courseCodes") or []) if c]

        ratings = (node.get("ratings") or {})
        for edge in ratings.get("edges", []):
            rv = edge.get("node") or {}
            if not rv:
                continue
            # Attach FK + coarse flatten
            rv_clean = {
                "professor_id": details.get("id") if details else teacher_id,
                "review_id": rv.get("id") or rv.get("legacyId"),
                "class": rv.get("class"),
                "rating": rv.get("qualityRating"),
                "difficulty": rv.get("difficultyRating"),
                "comment": rv.get("comment"),
                "date": rv.get("date"),
                "grade": rv.get("grade"),
                "would_take_again": rv.get("wouldTakeAgain"),
                "helpful": rv.get("helpfulRating"),
                "clarity": rv.get("clarityRating"),
                "is_online": rv.get("isForOnlineClass"),
                "attendance_mandatory": rv.get("attendanceMandatory"),
                "textbook_use": rv.get("textbookUse"),
            }
            reviews.append(rv_clean)

        page = ratings.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        after = page.get("endCursor")
        time.sleep(0.4)

    return details or {"id": teacher_id}, reviews

# ---------------------------
# Orchestration
# ---------------------------

def run(school_id: int, max_profs: int = 0, with_reviews: bool = True, outdir: str = "data", query: str = "") -> None:
    profs_path = os.path.join(outdir, "professors.jsonl")
    reviews_path = os.path.join(outdir, "reviews.jsonl")

    prof_rows: List[Dict[str, Any]] = []
    review_rows: List[Dict[str, Any]] = []

    print(f"Fetching professors for school_id={school_id}, query='{query}'")
    all_profs = list(iter_professors(school_id, query=query))
    print(f"Found {len(all_profs)} professors")
    if max_profs > 0:
        all_profs = all_profs[:max_profs]

    for node in tqdm(all_profs, desc="Professors"):
        pid = node.get("id") or node.get("legacyId")
        if with_reviews:
            details, rvs = fetch_prof_details_and_reviews(pid)
            prof_rows.append(details)
            review_rows.extend(rvs)
        else:
            # Keep just summary fields from search node
            row = {
                "id": node.get("id"),
                "legacyId": node.get("legacyId"),
                "firstName": node.get("firstName"),
                "lastName": node.get("lastName"),
                "department": node.get("department"),
                "avgRating": node.get("avgRating"),
                "numRatings": node.get("numRatings"),
                "avgDifficulty": node.get("avgDifficulty"),
                "wouldTakeAgainPercent": node.get("wouldTakeAgainPercent"),
                "school": node.get("school"),
            }
            prof_rows.append(row)
        time.sleep(0.2)

    dump_jsonl(profs_path, prof_rows)
    if with_reviews:
        dump_jsonl(reviews_path, review_rows)

    # Compact summary JSON for quick lookups
    compact = [
        {
            "id": r.get("id"),
            "name": f"{r.get('firstName','')} {r.get('lastName','')}".strip(),
            "department": r.get("department"),
            "avgRating": r.get("avgRating"),
            "numRatings": r.get("numRatings"),
            "avgDifficulty": r.get("avgDifficulty"),
        }
        for r in prof_rows
    ]
    write_json(os.path.join(outdir, "professors_min.json"), compact)

    print(f"\n✅ Done. Wrote {len(prof_rows)} professors → {profs_path}")
    if with_reviews:
        print(f"✅ Wrote {len(review_rows)} reviews → {reviews_path}")
    print(f"✅ Compact index → {os.path.join(outdir, 'professors_min.json')}")

# ---------------------------
# Optional: Playwright fallback (profile pages)
# ---------------------------
# This fallback is provided for completeness and is OFF by default. It focuses on core
# fields and skips full review text. If you need it, uncomment the imports and wire
# it into `run()` when GraphQL fails for you.

# from playwright.sync_api import sync_playwright
# def crawl_with_playwright(list_url: str, max_pages: int = 50) -> List[Dict[str, Any]]:
#     out: List[Dict[str, Any]] = []
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=True)
#         ctx = browser.new_context(user_agent=UA)
#         page = ctx.new_page()
#         page.goto(list_url)
#         for _ in range(max_pages):
#             try:
#                 page.get_by_role("button", name="Show More").click(timeout=2000)
#                 time.sleep(0.5)
#             except Exception:
#                 break
#         cards = page.locator("[data-qa='teacher-card']").all()
#         for c in cards:
#             name = c.locator("[data-qa='name']").inner_text(timeout=1000)
#             dept = c.locator("[data-qa='department']").inner_text(timeout=1000)
#             rating = c.locator("[data-qa='quality']").inner_text(timeout=1000)
#             num = c.locator("[data-qa='num-ratings']").inner_text(timeout=1000)
#             out.append({"name": name, "department": dept, "avgRating": rating, "numRatings": num})
#         browser.close()
#     return out

# ---------------------------
# CLI
# ---------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RMP → JSON scraper for PSU")
    parser.add_argument("--school-id", type=int, default=758, help="RMP school ID (PSU=758)")
    parser.add_argument("--max-profs", type=int, default=0, help="Limit professors (0 = no limit)")
    parser.add_argument("--reviews", choices=["yes", "no"], default="yes", help="Include full reviews")
    parser.add_argument("--outdir", type=str, default="data")
    parser.add_argument("--query", type=str, default="", help="Search query text (default: empty string for all)")
    args = parser.parse_args()

    run(
        school_id=args.school_id,
        max_profs=args.max_profs,
        with_reviews=(args.reviews == "yes"),
        outdir=args.outdir,
        query=args.query,
    )