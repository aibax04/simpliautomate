# Deployment Guide (Render Free Tier)

This application is ready for deployment on Render.

## Step 1: Create a PostgreSQL Database
1. Log in to [Render](https://dashboard.render.com).
2. Click **New** -> **Database**.
3. Name it `simplii-db`.
4. Choose the **Free** tier.
5. Once created, copy the **Internal Database URL** (if deploying backend on Render) or **External Database URL**. Use the one that starts with `postgres://`.
   - **Crucial:** Change `postgres://` to `postgresql+asyncpg://` when setting the `DATABASE_URL` environment variable.

## Step 2: Deploy the Web Service
1. Click **New** -> **Web Service**.
2. Connect your GitHub repository.
3. **Runtime:** `Python`.
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.server:app`
6. Click **Advanced** to add Environment Variables.

## Required Environment Variables
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host/db` |
| `GEMINI_API_KEY` | Your Google Gemini API Key |
| `SECRET_KEY` | A long random string for JWT signing |
| `SECRET_KEY_APP` | Shared secret for Signup/Login forms (e.g. `simplii-123`) |
| `LINKEDIN_CLIENT_ID` | (Optional) LinkedIn App ID |
| `LINKEDIN_CLIENT_SECRET` | (Optional) LinkedIn App Secret |
| `LINKEDIN_REDIRECT_URI` | Your Render URL + `/api/auth/linkedin/callback` |
| `LINKEDIN_ACCESS_TOKEN` | (Existing) Token if manually set |
| `LINKEDIN_USER_URN` | (Existing) URN if manually set |

## Free Tier Limitations
- **Spin-down:** Render free web services spin down after 15 minutes of inactivity. The first request after a spin-down can take 30+ seconds.
- **Database:** Free databases expire after 90 days.
- **Memory:** 512MB limit. The background news fetcher is optimized but watch for OOM if many users connect simultaneously.

## Database Migrations
The app is configured to verify connection on startup. For the first deployment, the models will be created if they don't exist (ensure `Base.metadata.create_all` equivalent is called if not using Alembic explicitly).

