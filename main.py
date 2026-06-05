#!/usr/bin/env python3
"""Sync daily curated news from newsdata.io into a Notion database.

For each configured category the script:
  1. fetches the latest free-tier news from newsdata.io,
  2. inserts de-duplicated rows into a Notion database, and
  3. creates a per-category page with metadata.

Key environment variables (see README for the full table):
  NEWSDATA_API_KEY        (required) free key from https://newsdata.io
  NOTION_API_KEY          (required) Notion integration secret
  NOTION_PARENT_PAGE_ID   (required first run) page the integration can edit
  NOTION_DATABASE_ID      (optional) reuse an existing database
"""
import argparse
import os
import sys
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from newsdata_client import NewsDataClient, NewsDataError
from notion_sync import NotionSync, NotionError


def _split(value, fallback):
    items = [c.strip() for c in (value or "").split(",") if c.strip()]
    return items or fallback


def main():
    parser = argparse.ArgumentParser(
        description="Sync newsdata.io news into a Notion database."
    )
    parser.add_argument("--categories", help="Comma-separated categories override.")
    parser.add_argument("--max", type=int, help="Max articles per category.")
    parser.add_argument("--no-pages", action="store_true",
                        help="Skip creating per-category Notion pages.")
    args = parser.parse_args()

    parent_page = os.environ.get("NOTION_PARENT_PAGE_ID")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not parent_page and not database_id:
        sys.exit("Set NOTION_PARENT_PAGE_ID (to create a database) or "
                 "NOTION_DATABASE_ID (to reuse one).")

    categories = _split(
        args.categories or os.environ.get("NEWS_CATEGORIES"),
        ["top", "technology", "business"],
    )
    try:
        max_articles = args.max or int(os.environ.get("MAX_ARTICLES", "8"))
    except ValueError:
        max_articles = 8
    country = os.environ.get("NEWS_COUNTRY") or None
    language = os.environ.get("NEWS_LANGUAGE", "en")

    try:
        news = NewsDataClient()
        notion = NotionSync()
    except (NewsDataError, NotionError) as exc:
        sys.exit(str(exc))

    if not database_id:
        try:
            database_id = notion.ensure_database(parent_page)
            print(f"Created Notion database: {database_id}")
            print("Tip: set NOTION_DATABASE_ID to reuse it next time.")
        except NotionError as exc:
            sys.exit(f"Could not create database: {exc}")

    when = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_added = 0

    for category in categories:
        print(f"\n== {category} ==")
        try:
            articles = news.fetch_news(
                category=category,
                country=country,
                language=language,
                max_articles=max_articles,
            )
        except NewsDataError as exc:
            print(f"  skipped: {exc}")
            continue

        if not articles:
            print("  no articles returned.")
            continue

        added = 0
        for art in articles:
            try:
                if notion.url_exists(database_id, art.get("link")):
                    continue
                notion.add_article(database_id, art, category)
                added += 1
            except NotionError as exc:
                print(f"  could not add '{art.get('title')}': {exc}")
        total_added += added
        print(f"  added {added} new / {len(articles)} fetched")

        if not args.no_pages and parent_page:
            try:
                notion.create_category_page(parent_page, category, articles, when)
                print(f"  category page created for '{category}'")
            except NotionError as exc:
                print(f"  could not create category page: {exc}")

    print(f"\nDone. {total_added} new article(s) synced to Notion.")


if __name__ == "__main__":
    main()
