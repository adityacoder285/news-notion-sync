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
- 🛟 Free-tier safe: gracefully handles invalid keys (401), rate limits (429),
  paid-only parameters (403/422), and empty results.

## How it works

For each configured category the script:

1. fetches the latest news from newsdata.io (following the `nextPage` token),
2. inserts de-duplicated rows into your Notion database, then
3. creates a per-category Notion page with a metadata callout.

## Requirements

- Python 3.9+
- A free newsdata.io API key — sign up at <https://newsdata.io>
- A Notion integration token + a parent page the integration can edit

## Setup

### 1. Install

```bash
git clone https://github.com/your-username/news-notion-sync.git
cd news-notion-sync
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

### 2. Get your newsdata.io key

Create a free account at <https://newsdata.io> and copy your API key from the
dashboard. The key is **never hardcoded** — it is read from the
`NEWSDATA_API_KEY` environment variable.

### 3. Create a Notion integration

1. Go to <https://www.notion.so/my-integrations> and create a new integration.
2. Copy the **Internal Integration Secret** → this is your `NOTION_API_KEY`.
3. Open (or create) a Notion page that will hold your news, click the `•••`
   menu → **Connections** → add your integration so it can edit the page.
4. Copy that page's ID from its URL (the 32-character hex string) →
   `NOTION_PARENT_PAGE_ID`.

### 4. Configure environment variables

Copy the example file and fill it in:

```bash
cp .env.example .env
```

Or export them directly in your shell:

```bash
export NEWSDATA_API_KEY="your_newsdata_key"
export NOTION_API_KEY="secret_your_notion_token"
export NOTION_PARENT_PAGE_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

## Configuration

| Variable                | Required | Default                    | Description |
|-------------------------|----------|----------------------------|-------------|
| `NEWSDATA_API_KEY`      | ✅       | —                          | Your free newsdata.io key |
| `NOTION_API_KEY`        | ✅       | —                          | Notion integration secret |
| `NOTION_PARENT_PAGE_ID` | ✅*      | —                          | Page used to create the database + category pages |
| `NOTION_DATABASE_ID`    | ⬜       | —                          | Reuse an existing database instead of creating one |
| `NEWS_CATEGORIES`       | ⬜       | `top,technology,business`  | Comma-separated categories |
| `NEWS_LANGUAGE`         | ⬜       | `en`                       | Language code |
| `NEWS_COUNTRY`          | ⬜       | —                          | Country code, e.g. `us` |
| `MAX_ARTICLES`          | ⬜       | `8`                        | Max articles per category |

\* `NOTION_PARENT_PAGE_ID` is required the first time (to create the database). On
later runs you can set `NOTION_DATABASE_ID` to reuse the database — though the
parent page is still needed for per-category pages.

## Usage

```bash
python main.py
```

Useful flags:

```bash
python main.py --categories "top,sports,science"   # override categories
python main.py --max 5                              # fewer articles per category
python main.py --no-pages                           # database only, skip pages
```

On first run you'll see the new database ID printed — save it as
`NOTION_DATABASE_ID` to reuse the same database afterwards.

## Scheduling a daily sync

Run it once a day with cron (adjust the path and time):

```cron
0 8 * * *  cd /path/to/news-notion-sync && /path/to/.venv/bin/python main.py >> sync.log 2>&1
```

## Free tier vs. paid

Everything in this project works on the newsdata.io **free plan**. The following
newsdata.io capabilities require a **paid plan** and are intentionally **not**
used here:

- `sentiment` / sentiment analysis
- AI fields: `ai_tag`, `ai_region`, `ai_org`, `ai_summary`
- the historical `/archive` endpoint and long date ranges
- advanced full-text query operators

If newsdata.io rejects a request because a parameter needs a paid plan (HTTP
403/422), the script reports it clearly and continues with the next category
instead of crashing.

## Project layout

```
main.py             # orchestrates the sync
newsdata_client.py  # thin newsdata.io /news client (free-tier safe)
notion_sync.py      # minimal Notion API helper
requirements.txt
.env.example
```

## License

MIT — use it, fork it, ship it.
