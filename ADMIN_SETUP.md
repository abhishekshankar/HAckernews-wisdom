# Admin Dashboard Setup Guide

## Phase 1: Backend Foundation ✅ Complete

You now have the admin dashboard backend foundation with:
- FastAPI server for admin operations
- Session-based authentication with bcrypt password hashing
- Database utilities for admin tables
- Basic frontend with login page and navigation

## Setup Instructions

### Step 1: Apply Database Schema

The admin dashboard requires new tables in your Supabase database.

1. Open your Supabase dashboard: https://app.supabase.com
2. Go to **SQL Editor** → **New Query**
3. Copy and paste the admin schema extension at the bottom of `schema.sql`:

```sql
-- Admin tables
create table if not exists admin_users (
  id bigserial primary key,
  username text unique not null,
  password_hash text not null,
  email text,
  created_at timestamp default now(),
  last_login timestamp
);

create table if not exists scraper_runs (
  id bigserial primary key,
  started_at timestamp not null,
  completed_at timestamp,
  status text not null,
  trigger_type text not null,
  triggered_by text,
  stories_processed int default 0,
  errors_count int default 0,
  config jsonb,
  logs text,
  error_message text
);

create table if not exists system_config (
  key text primary key,
  value jsonb not null,
  updated_at timestamp default now(),
  updated_by text
);

create table if not exists audit_log (
  id bigserial primary key,
  timestamp timestamp default now(),
  username text not null,
  action text not null,
  entity_type text,
  entity_id bigint,
  old_value jsonb,
  new_value jsonb
);

-- Indexes
create index if not exists idx_scraper_runs_status on scraper_runs(status);
create index if not exists idx_scraper_runs_started on scraper_runs(started_at desc);
create index if not exists idx_audit_log_timestamp on audit_log(timestamp desc);
create index if not exists idx_audit_log_username on audit_log(username);

-- Default configuration
insert into system_config (key, value, updated_by) values
  ('scraper.hn_limit', '100', 'system'),
  ('scraper.story_types', '["topstories","newstories","showstories","askstories","jobstories"]', 'system'),
  ('scraper.enabled', 'true', 'system'),
  ('categorization.keywords', '{"AI/ML":["ai","ml","llm","machine learning","neural","model"],"Security":["security","vuln","crypto","encryption","attack"],"Web Development":["web","frontend","backend","api","javascript"],"DevOps":["devops","sre","observability","k8s","kubernetes"],"Databases":["database","postgres","mysql","sqlite","query"],"Startups":["startup","founder","funding","venture"],"Career":["career","hiring","interview","salary"],"Show HN":["show hn"],"Ask HN":["ask hn"],"Jobs":["hiring","job","jobs"]}', 'system')
on conflict (key) do nothing;
```

4. Click **Run**

✅ If successful, you should see 4 tables created.

### Step 2: Install Dependencies

```bash
cd "/Users/abhi/Documents/Problem Discovery/HAckernews-wisdom"
pip install -r requirements.txt
```

This installs:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `passlib[bcrypt]` - Password hashing
- `python-multipart` - Form data handling

### Step 3: Create Admin User

```bash
cd "/Users/abhi/Documents/Problem Discovery/HAckernews-wisdom"
export SUPABASE_DB_URL="your-supabase-connection-url"
python -m backend.admin_server create-admin \
  --username admin \
  --password <your-secure-password> \
  --email your-email@example.com
```

**Example:**
```bash
python -m backend.admin_server create-admin \
  --username admin \
  --password MySecurePassword123 \
  --email you@example.com
```

You should see:
```
✓ Admin user created: admin (ID: 1)
```

### Step 4: Start the Admin Server

**Terminal 1: Admin Server**
```bash
cd "/Users/abhi/Documents/Problem Discovery/HAckernews-wisdom"
export SUPABASE_DB_URL="your-supabase-connection-url"
python -m backend.admin_server
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
Open http://localhost:8000/admin in your browser
```

**Terminal 2: Config Server** (for public dashboard)
```bash
cd "/Users/abhi/Documents/Problem Discovery/HAckernews-wisdom"
export SUPABASE_URL="https://xxx.supabase.co"
export SUPABASE_ANON_KEY="eyJxxx..."
export CONFIG_SERVER_PORT=9876
python backend/admin_server.py
```

### Step 5: Access the Dashboard

Open your browser and go to:
```
http://localhost:8000/admin
```

**Login with:**
- Username: `admin`
- Password: (the password you created in Step 3)

## What's Working Right Now (Phase 1)

✅ **Authentication**
- Login/logout with session cookies
- Password validation with bcrypt
- User session tracking

✅ **Admin Dashboard Interface**
- Login page
- Dashboard navigation
- Scraper control panel (UI only, backend in Phase 2)

## What's Coming in Phase 2 (Next)

🔄 **Scraper Control API**
- Trigger scrapes on-demand
- Monitor progress in real-time
- View scraper run history and logs
- WebSocket updates for live monitoring

🔄 **Data Management API** (Phase 3)
- Edit stories and metadata
- Manage categories and keywords
- Manage clusters
- Bulk operations

🔄 **Analytics Dashboard** (Phase 4)
- Overview statistics
- Trend analysis
- Scraper performance metrics

## Troubleshooting

### "ModuleNotFoundError: No module named 'fastapi'"
**Solution:** Install requirements:
```bash
pip install -r requirements.txt
```

### "Missing SUPABASE_DB_URL environment variable"
**Solution:** Set the environment variable before running:
```bash
export SUPABASE_DB_URL="postgresql://user:pass@host:port/dbname"
python -m backend.admin_server
```

### "relation "admin_users" does not exist"
**Solution:** Run the schema.sql admin tables in Supabase SQL Editor first (Step 1)

### "Address already in use" on port 8000
**Solution:** Use a different port:
```bash
export ADMIN_PORT=8001
python -m backend.admin_server
```

Then access at: `http://localhost:8001/admin`

### "Invalid username or password" when logging in
**Solution:** Make sure you created the admin user (Step 3) and are using the correct credentials

## File Structure

```
HAckernews-wisdom/
├── backend/                    # New admin backend
│   ├── admin_server.py        # FastAPI app entry point
│   ├── auth.py                # Login/session management
│   ├── database.py            # Database utilities
│   ├── models.py              # Pydantic models
│   └── routers/               # API endpoint routers (coming in Phase 2)
│
├── frontend/
│   ├── admin-dashboard.html   # Admin UI
│   ├── admin-dashboard.js     # Client-side logic
│   └── admin-dashboard.css    # Styling
│
├── daily-wisdom.* (unchanged)  # Public dashboard still works
├── scrape_hn.py (unchanged)    # Scraper still works
└── export_daily.py (unchanged) # Export still works
```

## What to Do Next

**Option 1: Continue with Phase 2 Immediately**
- I can build the Scraper Control API so you can trigger scrapes and monitor them

**Option 2: Test Phase 1 First**
- Verify login/logout works
- Make sure database tables exist
- Check that the admin user was created

Just let me know! The foundation is solid and we can build the rest incrementally.

## Security Notes

**Current Setup (Local Development):**
- ✅ Passwords hashed with bcrypt (12 rounds)
- ✅ Session cookies with HttpOnly flag
- ✅ CORS restricted to localhost
- ✅ No sensitive data in frontend code
- ✅ Supabase credentials served via config endpoint

**For Production Deployment:**
- Add HTTPS with Let's Encrypt
- Use stronger session secret
- Set up proper firewall rules
- Enable rate limiting
- Add CSRF protection
- Use environment variables for secrets

---

**Questions?** Let me know and I'll help you get everything running!
