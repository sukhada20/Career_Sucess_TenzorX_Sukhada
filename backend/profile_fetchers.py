"""
Real-data profile fetchers for GitHub, LinkedIn, Naukri.

Returns (profile_data_dict, live_data_bool, source_label) per provider.
Falls back gracefully to None when a provider is unreachable, rate-limited,
or unconfigured — caller is expected to use the synthesizer as fallback.
"""
import os
import re
import httpx
from typing import Optional

# ── Timeouts & UA ─────────────────────────────────────────────
HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=8.0, write=5.0, pool=5.0)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # optional — lifts rate limit to 5000/hr
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
PDL_API_KEY = os.getenv("PDL_API_KEY")  # People Data Labs — real LinkedIn enrichment (free tier: 100 credits)
PROXYCURL_API_KEY = os.getenv("PROXYCURL_API_KEY")  # alt LinkedIn enrichment


# ───────────────────────────────────────────────────────────────
# GitHub — fully real public API
# ───────────────────────────────────────────────────────────────
def fetch_github(username: str) -> Optional[dict]:
    """Returns real GitHub profile data, or None on failure/rate-limit."""
    username = username.strip().lstrip("@")
    if not username or "/" in username:
        return None
    headers = {"Accept": "application/vnd.github+json", "User-Agent": UA}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, headers=headers, follow_redirects=True) as client:
            r = client.get(f"https://api.github.com/users/{username}")
            if r.status_code != 200:
                return None
            user = r.json()

            # Fetch up to 30 most-recent repos for stars + language signals
            r2 = client.get(f"https://api.github.com/users/{username}/repos?per_page=30&sort=updated")
            repos = r2.json() if r2.status_code == 200 else []

            stars = sum((repo.get("stargazers_count") or 0) for repo in repos)
            langs = {}
            for repo in repos:
                lang = repo.get("language")
                if lang:
                    langs[lang] = langs.get(lang, 0) + 1
            top_langs = sorted(langs.keys(), key=lambda L: -langs[L])[:5]

            return {
                "username": user.get("login"),
                "avatar_url": user.get("avatar_url"),
                "name": user.get("name"),
                "bio": user.get("bio"),
                "public_repos": user.get("public_repos", 0),
                "followers": user.get("followers", 0),
                "following": user.get("following", 0),
                "stars_earned": stars,
                "contributions_last_year": None,  # GraphQL-only; left null in live mode
                "current_streak_days": None,
                "top_languages": top_langs,
                "profile_url": user.get("html_url"),
                "created_at": (user.get("created_at") or "")[:10],
                "_source": "Live · GitHub REST API",
            }
    except Exception:
        return None


def github_score(data: dict) -> int:
    """Map real GitHub data → 0-100 score (same shape as synthesizer's score)."""
    repos = data.get("public_repos", 0)
    stars = data.get("stars_earned", 0)
    followers = data.get("followers", 0)
    score = 20 + repos * 0.5 + min(stars, 200) * 0.15 + min(followers, 500) * 0.05
    return max(0, min(100, int(score)))


# ───────────────────────────────────────────────────────────────
# LinkedIn — public Open Graph parse (best-effort, no scraping past auth wall)
# ───────────────────────────────────────────────────────────────
_OG_RX = re.compile(r'<meta\s+property="og:([a-z:]+)"\s+content="([^"]+)"', re.IGNORECASE)

def fetch_linkedin_pdl(username: str) -> Optional[dict]:
    """Real LinkedIn enrichment via People Data Labs (when PDL_API_KEY is set).
    Free tier: 100 credits on signup at https://dashboard.peopledatalabs.com.
    Returns rich profile data (name, headline, jobs, skills, education) on success."""
    if not PDL_API_KEY:
        return None
    username = re.sub(r"[^a-zA-Z0-9\-_]", "", username.strip().lstrip("@"))
    if not username:
        return None
    url = "https://api.peopledatalabs.com/v5/person/enrich"
    params = {"profile": f"linkedin.com/in/{username}", "min_likelihood": 6}
    headers = {"X-Api-Key": PDL_API_KEY, "Accept": "application/json"}
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, headers=headers) as client:
            r = client.get(url, params=params)
            if r.status_code != 200:
                return None
            payload = r.json()
            d = payload.get("data") or {}
            if not d:
                return None
            jobs = d.get("experience") or []
            skills = [s.get("name") for s in (d.get("skills") or []) if s.get("name")][:8]
            education = d.get("education") or []
            current_job = next((j for j in jobs if j.get("is_primary")), jobs[0] if jobs else {})
            return {
                "username": username,
                "name": d.get("full_name") or f"{d.get('first_name','')} {d.get('last_name','')}".strip(),
                "headline": d.get("job_title") or d.get("headline"),
                "current_company": (current_job.get("company") or {}).get("name"),
                "current_role": current_job.get("title", {}).get("name") if isinstance(current_job.get("title"), dict) else current_job.get("title"),
                "location": d.get("location_name"),
                "connections": d.get("linkedin_connections"),
                "top_skills": skills,
                "education": [
                    {
                        "school": (e.get("school") or {}).get("name"),
                        "degree": (e.get("degrees") or [None])[0],
                        "ended_year": e.get("end_date"),
                    } for e in education[:3]
                ],
                "experience_count": len(jobs),
                "avatar_url": None,  # PDL doesn't return photos
                "profile_url": f"https://www.linkedin.com/in/{username}/",
                "_source": "Live · People Data Labs (real LinkedIn enrichment)",
            }
    except Exception:
        return None


def fetch_linkedin_proxycurl(username: str) -> Optional[dict]:
    """Real LinkedIn enrichment via Proxycurl. Returns photo + rich profile.
    Free tier: 10 credits (one-time)."""
    if not PROXYCURL_API_KEY:
        return None
    username = re.sub(r"[^a-zA-Z0-9\-_]", "", username.strip().lstrip("@"))
    if not username:
        return None
    url = "https://nubela.co/proxycurl/api/v2/linkedin"
    params = {"url": f"https://www.linkedin.com/in/{username}/", "fallback_to_cache": "on-error"}
    headers = {"Authorization": f"Bearer {PROXYCURL_API_KEY}"}
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, headers=headers) as client:
            r = client.get(url, params=params)
            if r.status_code != 200:
                return None
            d = r.json()
            exp = d.get("experiences") or []
            current = exp[0] if exp else {}
            return {
                "username": username,
                "name": d.get("full_name") or f"{d.get('first_name','')} {d.get('last_name','')}".strip(),
                "headline": d.get("headline") or d.get("occupation"),
                "current_company": current.get("company"),
                "current_role": current.get("title"),
                "location": ", ".join(filter(None, [d.get("city"), d.get("country_full_name")])) or None,
                "connections": d.get("connections"),
                "top_skills": (d.get("skills") or [])[:8],
                "education": [
                    {
                        "school": e.get("school"),
                        "degree": e.get("degree_name"),
                        "ended_year": (e.get("ends_at") or {}).get("year"),
                    } for e in (d.get("education") or [])[:3]
                ],
                "experience_count": len(exp),
                "avatar_url": d.get("profile_pic_url"),
                "profile_url": f"https://www.linkedin.com/in/{username}/",
                "_source": "Live · Proxycurl (real LinkedIn enrichment)",
            }
    except Exception:
        return None


def fetch_linkedin(username: str) -> Optional[dict]:
    """Best-effort public-profile probe.

    Hits https://www.linkedin.com/in/{username}/ and extracts Open Graph tags
    from the response HTML if LinkedIn returns the page (often it doesn't —
    they aggressively bot-detect non-authenticated traffic). Returns None
    if the page can't be parsed; caller then falls back to synthesis.

    What you typically get when it works:
      - og:title  → "Name - Headline | LinkedIn"
      - og:image  → profile photo CDN URL
      - og:description → snippet
    """
    username = re.sub(r"[^a-zA-Z0-9\-_]", "", username.strip().lstrip("@"))
    if not username:
        return None
    url = f"https://www.linkedin.com/in/{username}/"
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, headers=headers, follow_redirects=True) as client:
            r = client.get(url)
            # LinkedIn returns 999 for many bot-suspected requests; 200 means HTML was served
            if r.status_code != 200:
                return {
                    "username": username,
                    "profile_url": url,
                    "url_reachable": False,
                    "http_status": r.status_code,
                    "_source": f"Live probe · LinkedIn returned HTTP {r.status_code} (bot-detected — full data requires enterprise partnership)",
                }
            html = r.text
            tags = {k.lower(): v for k, v in _OG_RX.findall(html)}
            title = tags.get("title", "")
            # og:title is usually "Name - Headline | LinkedIn"
            name, headline = None, None
            m = re.match(r"(.+?)\s+-\s+(.+?)\s*\|\s*LinkedIn", title)
            if m:
                name, headline = m.group(1).strip(), m.group(2).strip()
            return {
                "username": username,
                "url_reachable": True,
                "name": name,
                "headline": headline,
                "og_description": tags.get("description"),
                "avatar_url": tags.get("image"),
                "profile_url": tags.get("url", url),
                "_source": "Live · LinkedIn public page (Open Graph)",
                "_partial": True,
                "_note": "Connections/skills/endorsements are not in the public profile and require LinkedIn enterprise partnership.",
            }
    except Exception as e:
        return {
            "username": username,
            "profile_url": url,
            "url_reachable": False,
            "_error": str(e)[:120],
            "_source": "Live probe failed",
        }


def linkedin_score(data: dict) -> int:
    """Score the LinkedIn payload. Rich enrichment (PDL/Proxycurl) scores higher
    than OG-only probe. Falls back to baseline if URL not reachable."""
    # Rich enrichment path — real data via PDL or Proxycurl
    if data.get("experience_count") is not None:
        score = 50
        if data.get("headline"):         score += 8
        if data.get("current_company"):  score += 10
        if (data.get("connections") or 0) > 100: score += 8
        score += min(15, (data.get("experience_count") or 0) * 3)
        if (data.get("top_skills") or []):       score += 5
        if (data.get("education") or []):        score += 4
        return min(100, score)
    # OG-only probe path
    if not data.get("url_reachable"):
        return 30  # baseline for "profile linked but data not accessible"
    score = 45
    if data.get("name"):     score += 10
    if data.get("headline"): score += 15
    if data.get("avatar_url"): score += 10
    return min(100, score)


# ───────────────────────────────────────────────────────────────
# Naukri-like cohort signal via Adzuna India (free public API)
# ───────────────────────────────────────────────────────────────
COURSE_KEYWORD_MAP = {
    "Engineering": "software engineer",
    "MBA":         "associate",
    "Nursing":     "nurse",
}
REGION_LOC_MAP = {
    "Bengaluru":   "Bangalore",
    "Hyderabad":   "Hyderabad",
    "Mumbai":      "Mumbai",
    "Pune":        "Pune",
    "Delhi NCR":   "Delhi",
    "Chennai":     "Chennai",
}

def fetch_naukri_cohort(course_type: str, region: str) -> Optional[dict]:
    """Fetches real cohort-level job-market data from Adzuna India.

    Returns count of open roles, average salary, and sample job titles for the
    borrower's course×region pair. Individual borrower activity (applications,
    recruiter views) is NOT fetchable via any public API — that stays simulated.

    Requires ADZUNA_APP_ID + ADZUNA_APP_KEY in env. Returns None if unconfigured.
    """
    if not (ADZUNA_APP_ID and ADZUNA_APP_KEY):
        return None
    keyword = COURSE_KEYWORD_MAP.get(course_type, course_type.lower())
    where = REGION_LOC_MAP.get(region, region)
    url = "https://api.adzuna.com/v1/api/jobs/in/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": keyword,
        "where": where,
        "results_per_page": 10,
        "content-type": "application/json",
    }
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            r = client.get(url, params=params)
            if r.status_code != 200:
                return None
            data = r.json()
            return {
                "open_roles_30d_estimate": data.get("count", 0),
                "avg_salary_inr": int(data.get("mean") or 0),
                "sample_titles": [j.get("title") for j in data.get("results", [])[:5]],
                "search_keyword": keyword,
                "search_location": where,
                "_source": "Live · Adzuna India jobs API",
            }
    except Exception:
        return None
