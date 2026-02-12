# Supabase PostgreSQL Setup Guide

This guide walks you through connecting the Raksha backend to a **free Supabase PostgreSQL** database instead of local SQLite.

---

## Step 1: Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up (GitHub login works).
2. Click **"New Project"**.
3. Fill in:
   - **Project Name:** `raksha-backend`
   - **Database Password:** Choose a strong password (**save this — you'll need it**)
   - **Region:** Choose the closest to your users (e.g., `South Asia (Mumbai)`)
4. Click **"Create new project"** and wait ~2 minutes for setup.

---

## Step 2: Get Your Connection String

1. In your Supabase dashboard, go to **Settings** → **Database**.
2. Scroll to **"Connection string"** section.
3. Select the **URI** tab.
4. Copy the connection string. It looks like:
   ```
   postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
5. **Replace `[YOUR-PASSWORD]`** in the string with the password you set in Step 1.

> ⚠️ Use the **"Transaction" pooler (port 6543)** connection for web apps, not the direct connection.

---

## Step 3: Update Your `.env`

Open `.env` in the project root and change the `DATABASE_URL` line:

```env
# Before (SQLite - local only)
# DATABASE_URL=sqlite:///raksha.db

# After (Supabase PostgreSQL - cloud)
DATABASE_URL=postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

Replace the URL with **your actual connection string** from Step 2.

---

## Step 4: Install PostgreSQL Driver

```bash
pip install psycopg2-binary
```

Or if using the project's requirements:
```bash
pip install -r requirements.txt
```

> `psycopg2-binary` is already included in `requirements.txt`.

---

## Step 5: Run Database Migrations

Since this is a fresh PostgreSQL database, you need to create all tables:

```bash
# Initialize migrations (skip if migrations/ folder already exists)
flask db init

# Generate migration from models
flask db migrate -m "Initial migration"

# Apply migration to create tables
flask db upgrade
```

If you get errors with `flask db migrate`, try:
```bash
# Delete old migrations and start fresh
rm -rf migrations/
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

---

## Step 6: Verify Connection

```bash
flask run --host=0.0.0.0 --port=5000
```

Then test:
```bash
# Register a user
curl -X POST http://localhost:5000/api/auth/register/email \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Password123!","full_name":"Test User"}'
```

If you get a successful `201` response, you're connected to Supabase! 🎉

---

## Step 7: View Your Data in Supabase

1. Go to your Supabase dashboard → **Table Editor**.
2. You should see all your tables: `users`, `trusted_contacts`, `sos_alerts`, etc.
3. You can browse, edit, and query data directly from the dashboard.

---

## Switching Back to SQLite (if needed)

Just change `.env` back:
```env
DATABASE_URL=sqlite:///raksha.db
```

No code changes required — SQLAlchemy handles both databases transparently.

---

## Free Tier Limits

Supabase free tier includes:
- **500 MB** database storage
- **Unlimited** API requests
- **2 projects** per account
- **Pauses after 1 week of inactivity** (just visit dashboard to resume)

This is more than enough for development and demo purposes.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `psycopg2` import error | Run `pip install psycopg2-binary` |
| `connection refused` | Check the connection string in `.env` (password, region, port) |
| `relation does not exist` | Run `flask db upgrade` to create tables |
| `SSL required` | Supabase enforces SSL by default — `psycopg2-binary` handles this automatically |
| Project paused | Visit the Supabase dashboard and click "Restore" |
