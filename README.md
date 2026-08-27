# news-notion-sync

Sync daily curated news from the [newsdata.io](https://newsdata.io) news API into a
Notion database — and auto-create a tidy page per category, each tagged with
metadata (article count, sync date, category).

This project is a small, dependency-light showcase of the **newsdata.io** REST API.
It runs out-of-the-box on the **free tier** — no paid features are required.

## Features

- 📰 Pulls the latest news from newsdata.io's `/news` endpoint, by category.
- 🗂️ Creates a Notion **database** (or reuses one you already have) with sensible
  columns: Title, Category, Source, Published, URL, Description.
- 🧷 **De-duplicates** by article URL so re-runs don't create duplicate rows.
- 📄 Auto-creates a **per-category page** with a metadata callout and a linked list
  of the day's articles.
- 🛠️ Free-tier safe: gracefully handles invalid keys (401), rate limits (429),
  paid-only parameters (403/422), and empty results.
- ⏰ Ships with a GitHub Actions workflow so the sync runs itself every morning.

## How it works

For each configured category the script

1. calls `GET https://newsdata.io/api/1/news` with free-tier-safe parameters
   (`apikey`, `category`, `language`, optional `country`), following `nextPage`
   until `MAX_ARTICLES` results are collected,
2. inserts the articles as rows in the Notion database, skipping any article URL
   that is already present, and
3. creates a per-category Notion page containing a metadata callout (category,
   sync date, article count) and a linked list of that day's articles.

## Quick start

```bash
git clone https://github.com/<you>/news-notion-sync.git
cd news-notion-sync

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then fill in your keys
python main.py
```

You need two free credentials:

- a **newsdata.io API key** — sign up at <https://newsdata.io>, and
- a **Notion integration token** — create one at
  <https://www.notion.so/my-integrations>, then share a parent page with the
  integration so it can create the database and pages.

## Configuration

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `NEWSDATA_API_KEY` | yes | — | Free newsdata.io API key. |
| `NOTION_API_KEY` | yes | — | Notion integration secret. |
| `NOTION_PARENT_PAGE_ID` | first run | — | Page the integration can edit. |
| `NOTION_DATABASE_ID` | no | — | Reuse an existing database instead of creating one. |
| `NEWS_CATEGORIES` | no | `top,technology,business` | Comma-separated categories. |
| `NEWS_LANGUAGE` | no | `en` | Language code. |
| `NEWS_COUNTRY` | no | — | Optional country filter. |
| `MAX_ARTICLES` | no | `8` | Max articles fetched per category. |

## Automated daily sync (GitHub Actions)

The workflow in [`.github/workflows/daily-sync.yml`](.github/workflows/daily-sync.yml)
runs `python main.py` every day at **07:00 UTC** (`cron: '0 7 * * *'`), and can also
be started by hand from the **Actions** tab via *Run workflow*.

Set the credentials it reads under **Settings → Secrets and variables → Actions → New repository secret**.
Create one secret each for `NEWSDATA_API_KEY`, `NOTION_API_KEY`, and `NOTION_PARENT_PAGE_ID` (add the optional `NOTION_DATABASE_ID` to reuse a database).
After saving them, trigger a manual run from the **Actions** tab to confirm the schedule will work — secrets are never printed in the logs.

Optional tuning values (`NEWS_CATEGORIES`, `NEWS_LANGUAGE`, `NEWS_COUNTRY`,
`MAX_ARTICLES`) are read from **repository variables** on the same settings page,
so they stay readable in the run logs.

### Running it with cron instead

Prefer your own machine? A plain crontab entry works the same way:

```cron
0 7 * * * cd /path/to/news-notion-sync && .venv/bin/python main.py >> sync.log 2>&1
```

## Free-tier notes

Only free-tier endpoints and parameters are used. Paid-only features (sentiment,
`ai_*` fields, `/archive`, advanced query operators) are intentionally left out,
and the client degrades gracefully if the API returns a rate-limit or
permission error.

## License

MIT
