"""Minimal Notion API helper for syncing news entries."""
import os

import requests

NOTION_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
TEXT_LIMIT = 1900  # Notion's rich_text hard limit is 2000 chars


class NotionError(Exception):
    """Raised when the Notion API cannot be used."""


def _rt(content):
    """Build a rich_text payload, safely truncated."""
    return [{"type": "text", "text": {"content": (content or "")[:TEXT_LIMIT]}}]


def _to_iso(pub_date):
    """Convert 'YYYY-MM-DD HH:MM:SS' to ISO 8601 for a Notion date."""
    if not pub_date:
        return None
    value = str(pub_date).strip().replace(" ", "T")
    return value or None


class NotionSync:
    """Small wrapper around the Notion REST API for news syncing."""

    def __init__(self, token=None, timeout=30):
        self.token = token or os.environ.get("NOTION_API_KEY")
        if not self.token:
            raise NotionError(
                "NOTION_API_KEY is not set. Create an integration at "
                "https://www.notion.so/my-integrations and export its secret."
            )
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        })

    def _request(self, method, path, payload=None):
        try:
            resp = self.session.request(method, NOTION_BASE + path,
                                        json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise NotionError(f"Network error contacting Notion: {exc}")

        if resp.status_code == 401:
            raise NotionError("Invalid Notion token (401). Check NOTION_API_KEY.")
        if resp.status_code == 429:
            raise NotionError("Notion rate limit (429). Slow down and retry.")
        if not resp.ok:
            raise NotionError(
                f"Notion API error {resp.status_code}: {resp.text[:300]}"
            )

        try:
            return resp.json()
        except ValueError:
            raise NotionError("Notion returned a non-JSON response.")

    # -- database -----------------------------------------------------------
    def ensure_database(self, parent_page_id, title="Daily News"):
        """Create a news database under the given parent page; return its id."""
        payload = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": _rt(title),
            "properties": {
                "Title": {"title": {}},
                "Category": {"select": {}},
                "Source": {"rich_text": {}},
                "Published": {"date": {}},
                "URL": {"url": {}},
                "Description": {"rich_text": {}},
            },
        }
        data = self._request("POST", "/databases", payload)
        return data["id"]

    def url_exists(self, database_id, url):
        """Return True if a row with this URL already exists (dedup)."""
        if not url:
            return False
        payload = {
            "filter": {"property": "URL", "url": {"equals": url}},
            "page_size": 1,
        }
        data = self._request("POST", f"/databases/{database_id}/query", payload)
        return bool(data.get("results"))

    def add_article(self, database_id, article, category):
        """Insert a single article as a database row."""
        title = article.get("title") or "(untitled)"
        props = {
            "Title": {"title": _rt(title)},
            "Category": {"select": {"name": category}},
            "Source": {"rich_text": _rt(article.get("source_id") or "unknown")},
            "Description": {"rich_text": _rt(article.get("description") or "")},
        }
        link = article.get("link")
        if link:
            props["URL"] = {"url": link}
        iso = _to_iso(article.get("pubDate"))
        if iso:
            props["Published"] = {"date": {"start": iso}}

        payload = {"parent": {"database_id": database_id}, "properties": props}
        return self._request("POST", "/pages", payload)

    # -- category pages -----------------------------------------------------
    def create_category_page(self, parent_page_id, category, articles, when):
        """Create a page for a category with a metadata callout + links."""
        heading = f"{category.title()} - {when}"
        children = [
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"type": "emoji", "emoji": "\U0001F5DE"},
                    "rich_text": _rt(
                        f"{len(articles)} articles - category: {category} - "
                        f"synced {when}"
                    ),
                },
            },
            {"object": "block", "type": "divider", "divider": {}},
        ]
        for art in articles:
            title = art.get("title") or "(untitled)"
            link = art.get("link")
            text_item = {"type": "text", "text": {"content": title[:TEXT_LIMIT]}}
            if link:
                text_item["text"]["link"] = {"url": link}
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [text_item]},
            })

        payload = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "properties": {"title": {"title": _rt(heading)}},
            "children": children[:100],  # Notion caps children at 100 per call
        }
        return self._request("POST", "/pages", payload)
