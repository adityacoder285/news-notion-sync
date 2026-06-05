"""Thin client for the newsdata.io REST API (free-tier safe)."""
import os
import time

import requests

BASE_URL = "https://newsdata.io/api/1"


class NewsDataError(Exception):
    """Raised when the newsdata.io API cannot be used."""


class NewsDataClient:
    """Fetches latest news from newsdata.io using only free-tier params."""

    def __init__(self, api_key=None, timeout=30):
        self.api_key = api_key or os.environ.get("NEWSDATA_API_KEY")
        if not self.api_key:
            raise NewsDataError(
                "NEWSDATA_API_KEY is not set. Get a free key at "
                "https://newsdata.io and export it before running."
            )
        self.timeout = timeout
        self.session = requests.Session()

    def fetch_news(self, category=None, country=None, language="en",
                   query=None, max_articles=10):
        """Return up to ``max_articles`` results, following the nextPage token."""
        collected = []
        next_page = None

        while len(collected) < max_articles:
            params = {"apikey": self.api_key}
            if language:
                params["language"] = language
            if category:
                params["category"] = category
            if country:
                params["country"] = country
            if query:
                params["q"] = query
            if next_page:
                params["page"] = next_page

            data = self._get("/news", params)
            batch = data.get("results") or []
            collected.extend(batch)

            next_page = data.get("nextPage")
            if not next_page or not batch:
                break
            time.sleep(1)  # be gentle with the free-tier rate limit

        return collected[:max_articles]

    def _get(self, path, params):
        try:
            resp = self.session.get(BASE_URL + path, params=params,
                                    timeout=self.timeout)
        except requests.RequestException as exc:
            raise NewsDataError(f"Network error contacting newsdata.io: {exc}")

        if resp.status_code == 401:
            raise NewsDataError("Invalid API key (401). Check NEWSDATA_API_KEY.")
        if resp.status_code == 429:
            raise NewsDataError(
                "Rate limit hit (429). The free tier is limited; wait a "
                "moment and try again."
            )
        if resp.status_code in (403, 422):
            raise NewsDataError(
                f"Request rejected ({resp.status_code}). A parameter may be "
                f"paid-only on your plan: {resp.text[:200]}"
            )
        if not resp.ok:
            raise NewsDataError(
                f"newsdata.io error {resp.status_code}: {resp.text[:200]}"
            )

        try:
            return resp.json()
        except ValueError:
            raise NewsDataError("newsdata.io returned a non-JSON response.")
