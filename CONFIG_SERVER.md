# Config Server Setup

The dashboard connects to Supabase via a secure config server that keeps your credentials server-side.

## How it Works

1. `config_server.py` reads `SUPABASE_URL` and `SUPABASE_ANON_KEY` from environment variables
2. Frontend calls `/api/config` to fetch these credentials
3. Frontend uses credentials to query Supabase REST API for live data
4. Falls back to local `daily-wisdom-data.json` if config server is unavailable

## Running the Config Server

### Prerequisites
- Python 3.x (no external dependencies required—uses only stdlib `http.server`)

### Setup

1. **Set environment variables:**
   ```bash
   export SUPABASE_URL="https://your-project.supabase.co"
   export SUPABASE_ANON_KEY="your-anon-key-here"
   ```

2. **Run the server:**
   ```bash
   python3 config_server.py
   ```

   Server will listen on `http://127.0.0.1:8080` by default.

   To use a different port:
   ```bash
   export CONFIG_SERVER_PORT=3000
   python3 config_server.py
   ```

3. **Test the endpoint:**
   ```bash
   curl http://127.0.0.1:8080/api/config
   ```

   Should return:
   ```json
   {
     "supabaseUrl": "https://your-project.supabase.co",
     "supabaseAnonKey": "your-anon-key-here"
   }
   ```

## Using with the Dashboard

1. Start the config server (step above)
2. Open `daily-wisdom.html` in your browser
3. Dashboard will automatically fetch config and use live Supabase data
4. If config server is unavailable, falls back to local JSON data

## Security Notes

- ✅ Secrets stay in environment variables (not in code)
- ✅ Frontend only gets credentials when server is running
- ✅ Anon key is meant for client-side use—it has restricted permissions
- ✅ Run config server on localhost; use reverse proxy (nginx) for production

## For Production

If deploying online:
1. Use HTTPS for config server
2. Implement CORS restrictions (limit to your domain)
3. Consider adding API key authentication for `/api/config`
4. Update `CONFIG_SERVER` in `daily-wisdom.js` to your server URL

## Troubleshooting

**"Config server unavailable"** in browser console?
- Make sure `config_server.py` is running
- Check that `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set
- Verify port matches `CONFIG_SERVER` in `daily-wisdom.js`

**Credentials not loading?**
- Check server logs: `python3 config_server.py`
- Verify `/api/config` returns correct values: `curl http://127.0.0.1:8080/api/config`

**Still seeing fallback data?**
- Check browser console for errors
- Verify Supabase URL and key are correct
- Ensure Supabase database has `daily_wisdom_view` table/view
