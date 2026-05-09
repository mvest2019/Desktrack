# Vercel Backend Deployment Context for Desktrack

## Project Structure

```
Desktrack/
├── backend/
│   ├── api/
│   │   └── index.py      # from main import app
│   ├── vercel.json       # Vercel config (see below)
│   ├── main.py           # FastAPI app (app = FastAPI(...))
│   ├── database.py
│   ├── models.py
│   ├── mongo.py
│   ├── schemas.py
│   └── requirements.txt
├── frontend/
│   ├── ...
```

## backend/vercel.json
```json
{
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

## backend/api/index.py
```python
from main import app
```

## Vercel Project Settings
- **Root Directory:** `backend`
- **Production Branch:** `main`
- **Environment Variables:**
  - `POSTGRES_URL`
  - `MONGODB_URL`
  - `MONGODB_DB_NAME`
  - `SECRET_KEY`
  - `ALGORITHM`
  - `ACCESS_TOKEN_EXPIRE_MINUTES`

## Problem
- Vercel keeps deploying the `initial commit` (old commit hash) even after new commits are pushed to `main`.
- The deployment always shows `403 Forbidden` and does not pick up the latest code.
- Root Directory is set to `backend`.
- GitHub repo is on `main` branch and contains the correct files.

## What I want
- Vercel to deploy the latest commit from the `main` branch in the `backend` directory, using the above config.
- The FastAPI backend should be accessible at the Vercel deployment URL.

---
