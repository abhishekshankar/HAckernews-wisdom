# Hackernews Wisdom Dashboard

Open `daily-wisdom.html` in a browser to view the dashboard.

## Data Scraping (Supabase + GitHub Actions)

### Required secret
Set `SUPABASE_DB_URL` in GitHub repo secrets.

### Manual run
```bash
SUPABASE_DB_URL="..." python HAckernews-wisdom/scrape_hn.py
SUPABASE_DB_URL="..." python HAckernews-wisdom/export_daily.py
```

### Daily schedule
The GitHub Action `.github/workflows/daily-scrape.yml` runs once per day at 03:00 UTC.
