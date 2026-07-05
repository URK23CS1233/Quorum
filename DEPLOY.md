# Quorum — Free Deployment Guide
# Backend → Render | Frontend → Vercel

---

## What You Need (all free)
- GitHub account — github.com
- Render account — render.com (sign in with GitHub)
- Vercel account — vercel.com (sign in with GitHub)
- Groq API key — console.groq.com (free, takes 1 minute)

---

## STEP 1 — Get a Free Groq API Key

1. Go to https://console.groq.com
2. Sign up / log in
3. Click "API Keys" in the left sidebar
4. Click "Create API Key"
5. Copy the key — it starts with `gsk_`
6. Save it somewhere safe (you'll need it in Step 3)

---

## STEP 2 — Push to GitHub

Open your terminal in the Quorum folder and run:

```bash
git add .
git commit -m "chore: prepare for deployment"
git push
```

If you haven't set up a GitHub repo yet:
1. Go to github.com → New repository → Name it "Quorum" → Create
2. Then run:
```bash
git remote add origin https://github.com/YOUR_USERNAME/Quorum.git
git branch -M main
git push -u origin main
```

---

## STEP 3 — Deploy Backend on Render (Free)

1. Go to https://render.com and sign in with GitHub

2. Click **"New +"** → **"Web Service"**

3. Connect your GitHub repo → select **Quorum**

4. Fill in these settings:
   - **Name**: quorum-backend
   - **Root Directory**: backend
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

5. Scroll down to **"Environment Variables"** and add:

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | `sqlite:///./quorum.db` |
   | `LLM_PROVIDER` | `groq` |
   | `LLM_MODEL` | `llama-3.3-70b-versatile` |
   | `GROQ_API_KEY` | `gsk_your_key_from_step_1` |
   | `JWT_SECRET` | any long random string e.g. `quorum-super-secret-jwt-2024` |
   | `CORS_ORIGINS` | `https://quorum.vercel.app` ← update after Step 4 |

6. Click **"Create Web Service"**

7. Wait ~3 minutes for it to build and deploy

8. **Copy your Render URL** — it looks like:
   `https://quorum-backend.onrender.com`

---

## STEP 4 — Deploy Frontend on Vercel (Free)

1. Go to https://vercel.com and sign in with GitHub

2. Click **"Add New Project"**

3. Import your **Quorum** GitHub repository

4. Fill in these settings:
   - **Root Directory**: frontend
   - **Framework Preset**: Next.js (auto-detected)
   - **Build Command**: `npm run build` (leave as is)
   - **Output Directory**: leave blank (Next.js default)

5. Click **"Environment Variables"** and add:

   | Key | Value |
   |-----|-------|
   | `BACKEND_URL` | `https://quorum-backend.onrender.com` ← your Render URL |
   | `NEXT_PUBLIC_WS_URL` | `wss://quorum-backend.onrender.com` ← same but wss:// |

6. Click **"Deploy"**

7. Wait ~2 minutes

8. **Copy your Vercel URL** — it looks like:
   `https://quorum-jillu.vercel.app`

---

## STEP 5 — Connect Frontend ↔ Backend (CORS Fix)

Now go back to Render and update CORS:

1. Open https://render.com → your **quorum-backend** service
2. Click **"Environment"** tab
3. Find `CORS_ORIGINS` and update its value to your Vercel URL:
   ```
   https://quorum-jillu.vercel.app
   ```
4. Click **"Save Changes"** — Render will redeploy automatically (~1 min)

---

## STEP 6 — Test It

1. Open your Vercel URL in the browser
2. Click **"Get Started"** → Register an account
3. You should see the dashboard with live metrics
4. Go to **Chat** and type anything — the AI should respond
5. Go to **Monitor** — you should see deployments loaded from memory

---

## Troubleshooting

**Backend not starting?**
- Check Render logs → "Logs" tab
- Most common issue: missing `GROQ_API_KEY`

**Frontend shows blank page?**
- Check Vercel logs → "Functions" tab
- Make sure `BACKEND_URL` has no trailing slash

**WebSocket not connecting?**
- Make sure `NEXT_PUBLIC_WS_URL` starts with `wss://` (not `ws://` or `https://`)

**CORS error in browser console?**
- Make sure `CORS_ORIGINS` in Render matches your Vercel URL exactly (no trailing slash)

**Render service sleeps after 15 min (free tier)?**
- Normal behavior on Render free tier — first request after sleep takes ~30 seconds
- For the hackathon demo, just open the backend URL first to wake it up

---

## Your Live URLs (fill in after deployment)

| Service | URL |
|---------|-----|
| Backend | https://____________.onrender.com |
| Frontend | https://____________.vercel.app |
| Health check | https://____________.onrender.com/health |
