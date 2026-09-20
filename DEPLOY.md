# 🚀 Deploying FinPilot on Render (Free Tier)

This guide walks you through deploying **FinPilot** as a single, unified web service on Render's free tier. In this architecture, FastAPI serves the React production bundle, the REST API, and auto-seeds a 6-month demo dataset on startup.

---

## 🌟 Highlights of the Live Demo Build

- **Single Web Service**: React SPA (`frontend/dist`) + FastAPI backend running together on port 8000.
- **Zero API Keys Required**: `LLM_PROVIDER=none` runs deterministic category rules, financial heuristics, and privacy sanitization at $0.00 cost.
- **Auto-Seeded 6-Month Dataset**: If the database is empty, FinPilot automatically seeds 152 Indian banking transactions, subscriptions (Netflix, Spotify, Prime), budgets, and goals on first boot.
- **Instant Demo Reset**: A "Reset demo data" button and endpoint (`POST /api/demo/reset`) restores the seed dataset anytime.
- **Sample Statement Ingestion**: A "Load Sample Statement" button imports a bundled 170-row HDFC bank statement with one click.
- **Safe Upload Limits**: 2 MB file cap in demo mode with active PII scrubbing.

---

## ⚡ Method A: Automatic Deployment via Blueprint (Recommended)

1. Sign in to **[Render.com](https://render.com)** (or create a free account).
2. Click **New +** in the top navigation and select **Blueprint**.
3. Connect your GitHub repository:
   ```
   KavyPatel68/finpilot
   ```
4. Render will read `render.yaml` and configure the service:
   - **Service Name**: `finpilot`
   - **Runtime**: Docker (`./Dockerfile`)
   - **Plan**: Free
   - **Health Check**: `/api/health`
   - **Environment Variables**:
     - `DEMO_MODE=true`
     - `LLM_PROVIDER=none`
     - `FRONTEND_DIST_DIR=/app/frontend/dist`
5. Click **Apply**.
6. Render builds the multi-stage Docker image and deploys your live site at `https://finpilot-xxxx.onrender.com`.

---

## 🛠️ Method B: Manual Web Service Deployment

If you prefer to configure manually without Blueprint:

1. In Render Dashboard, click **New +** -> **Web Service**.
2. Select **Build and deploy from a Git repository** and pick `KavyPatel68/finpilot`.
3. Set the following fields:
   | Setting | Value |
   | :--- | :--- |
   | **Name** | `finpilot` |
   | **Region** | `Oregon (US West)` or `Frankfurt (EU)` |
   | **Branch** | `main` |
   | **Runtime** | `Docker` |
   | **Dockerfile Path** | `./Dockerfile` |
   | **Docker Context** | `.` |
   | **Instance Type** | `Free` |

4. Scroll down to **Health Check Path** and set:
   ```
   /api/health
   ```

5. Under **Environment Variables**, add:
   | Key | Value |
   | :--- | :--- |
   | `DEMO_MODE` | `true` |
   | `LLM_PROVIDER` | `none` |
   | `FRONTEND_DIST_DIR` | `/app/frontend/dist` |
   | `DATABASE_URL` | `sqlite:///./data/finpilot.db` |
   | `CORS_ORIGINS` | `["*"]` |

6. Click **Deploy Web Service**.

---

## 💡 Important Notes on Render's Free Tier

> [!NOTE]
> **Free Tier Sleep / Cold Starts**:
> Render free web services spin down after **15 minutes of inactivity**. The first visit after spin-down takes approximately **40–50 seconds** to wake up. Subsequent requests respond instantly in milliseconds.

> [!TIP]
> **Optional Free AI Providers**:
> If you wish to activate live generative AI chat without credit cards, obtain a free API key from [Google AI Studio](https://aistudio.google.com/) or [Groq Cloud](https://console.groq.com/) and add either:
> - `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=your_key`
> - `LLM_PROVIDER=groq` and `GROQ_API_KEY=your_key`

---

## 🔍 Verification & Health Check

Once your deployment completes:

1. **SPA App**: Visit `https://finpilot-xxxx.onrender.com` -> The dashboard should load with 6 months of demo financial data.
2. **Health Check**: Visit `https://finpilot-xxxx.onrender.com/api/health` -> Returns `{"status":"ok","version":"1.0.0","db":"connected","demo_mode":true}`.
3. **Swagger UI**: Visit `https://finpilot-xxxx.onrender.com/docs` -> Interactive API documentation.
4. **SPA Reload**: Refresh `https://finpilot-xxxx.onrender.com/budgets` or `/reports` -> Loads seamlessly without 404 errors.
