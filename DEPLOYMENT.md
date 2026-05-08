# Syntra Staging Deployment Guide
### For a beginner deploying a real MVP for the first time

---

## The Big Picture — How Everything Connects

Before touching any command, understand **what each piece is** and **why it exists**.

```
  [Windows Desktop App]  ←──────────────────────────────────┐
      Syntra.exe                                             │  HTTP API calls
      (Python + Tkinter)                                     │  (login, screenshots,
                                                             │   activity logs)
                                                             ↓
  [Staging Server: 108.181.168.43]
  ┌────────────────────────────────────────────────────┐
  │  Nginx (port 80)                                   │
  │    ↓ forwards to                                   │
  │  FastAPI / Uvicorn (port 8000)                     │
  │    ↓ reads/writes to                               │
  │  PostgreSQL (users, auth)                          │
  │  MongoDB    (screenshots, activity logs)           │
  └────────────────────────────────────────────────────┘
         ↑
         │  reads data via browser
  [Next.js Frontend]
  (on Vercel — free hosting)
  https://your-app.vercel.app
```

**Rule of thumb:**
- The **desktop app** and **frontend website** are both "clients" — they talk TO the backend.
- The **backend** is the brain — it validates logins, stores data, serves screenshots.
- The **databases** are the memory — PostgreSQL for users, MongoDB for raw activity data.

---

## Folder Structure on the Server

When you clone the project to the server, it will look like this:

```
/opt/syntra/                    ← git repo root
  backend/                      ← FastAPI (Python)
    main.py
    database.py
    .env                        ← SECRET: passwords here, never commit
    requirements.txt
  frontend/                     ← Next.js (React)
    pages/
    package.json
  desktop/                      ← Windows app source (not needed on server)
    app.py
    syntra.spec
  deploy/                       ← All deployment scripts
    setup_server.sh
    deploy_backend.sh
    nginx.conf
    syntra-backend.service
  venv/                         ← Python virtual environment (created by setup script)
```

---

## Part 1 — Deploy the FastAPI Backend

### 1.1 What happens when you deploy the backend?

You are putting your Python API on a Linux server so it runs 24/7.

The chain is:
```
User's browser / app
  → Port 80 (Nginx)
    → Port 8000 (Uvicorn running your FastAPI code)
      → PostgreSQL (user data)
      → MongoDB    (screenshots)
```

**Nginx** is a "traffic cop" — it sits on port 80 (the normal web port) and forwards
requests to your Python process on port 8000. You use it because:
- Port 80 works without typing `:8000` in the URL
- Later you can add HTTPS (SSL) without changing your Python code

**Uvicorn** is the process that actually runs your Python code. Think of it as
"Python's web server" — it's what makes FastAPI accessible over the network.

**systemd** is the Linux process manager. It automatically:
- Starts your backend when the server reboots
- Restarts it if it crashes

### 1.2 One-time server setup (run once on a fresh server)

```bash
# SSH into your server
ssh root@108.181.168.43

# Clone the whole project
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git /opt/syntra

# Run setup (installs Python, Postgres, MongoDB, Nginx)
cd /opt/syntra
chmod +x deploy/setup_server.sh
./deploy/setup_server.sh
```

### 1.3 Create the .env file on the server

**This is the most important step.** Your backend needs passwords to connect to
the databases. These NEVER go into git — you create the file directly on the server.

```bash
# On the server:
cp /opt/syntra/backend/.env.staging /opt/syntra/backend/.env
nano /opt/syntra/backend/.env
```

Edit `ALLOWED_ORIGINS` to include your Vercel URL once you know it:
```
ALLOWED_ORIGINS=http://108.181.168.43,https://YOUR-APP.vercel.app,http://localhost:3000
```

Save with: `Ctrl+O` then `Enter` then `Ctrl+X`

### 1.4 Install the systemd service (runs backend on startup)

```bash
# On the server:
sudo cp /opt/syntra/deploy/syntra-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable syntra-backend    # auto-start on reboot
sudo systemctl start syntra-backend     # start now
```

Check that it's running:
```bash
sudo systemctl status syntra-backend
# You should see: Active: active (running)
```

### 1.5 Set up Nginx (reverse proxy)

```bash
# On the server:
sudo cp /opt/syntra/deploy/nginx.conf /etc/nginx/sites-available/syntra
sudo ln -s /etc/nginx/sites-available/syntra /etc/nginx/sites-enabled/syntra
sudo nginx -t                    # test for errors
sudo systemctl reload nginx
```

### 1.6 Test the backend

Open this in your browser:
```
http://108.181.168.43/docs
```
You should see the FastAPI interactive API documentation page.
If you see it — **the backend is deployed and working.**

### 1.7 Every future backend update

```bash
ssh root@108.181.168.43
cd /opt/syntra
./deploy/deploy_backend.sh
```

That script does: git pull → pip install → restart service. One command.

---

## Part 2 — Deploy the Next.js Frontend

### Option A: Vercel (recommended — free and takes 2 minutes)

Vercel is the company that made Next.js. They offer free hosting for Next.js apps.
No server configuration needed — they handle everything.

**Step 1: Push your code to GitHub** (if not already)

**Step 2: Create a Vercel account** at https://vercel.com (free, sign in with GitHub)

**Step 3: Import your project**
- Click "Add New Project"
- Select your GitHub repository
- Vercel auto-detects Next.js
- Set the "Root Directory" to `frontend`

**Step 4: Add environment variable in Vercel**
- In Vercel dashboard → Your project → Settings → Environment Variables
- Add:
  - Name: `NEXT_PUBLIC_API_URL`
  - Value: `http://108.181.168.43:8000`
  - Environment: Production + Preview + Development

**Step 5: Deploy**
- Click "Deploy"
- Vercel builds and deploys automatically
- You get a URL like `https://your-app.vercel.app`

**Step 6: Update CORS on your backend**
- Edit `/opt/syntra/backend/.env` on the server
- Add your Vercel URL to `ALLOWED_ORIGINS`:
  ```
  ALLOWED_ORIGINS=http://108.181.168.43,https://your-app.vercel.app,http://localhost:3000
  ```
- Restart backend: `sudo systemctl restart syntra-backend`

**Every future frontend update:** just push to GitHub. Vercel auto-deploys.

---

### Option B: Self-hosted on the same VPS (if you don't want Vercel)

```bash
# One-time: install Node.js and PM2 on the server
ssh root@108.181.168.43
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
npm install -g pm2

# Every update:
cd /opt/syntra
./deploy/deploy_frontend.sh
```

Then add a second nginx server block to proxy port 80 → port 3000 for your
frontend domain/IP. See `deploy/nginx.conf` for the pattern.

---

## Part 3 — Windows Desktop App: How It Connects to the Server

### 3.1 How the app talks to the backend

The desktop app uses the `requests` Python library to make HTTP calls — exactly
like your browser does when it loads a webpage, but from Python code.

```python
# This is what login looks like internally:
import requests

response = requests.post(
    "http://108.181.168.43:8000/api/login",
    json={"email": "user@example.com", "password": "secret"}
)
token = response.json()["access_token"]
# Now every future call includes: headers={"Authorization": f"Bearer {token}"}
```

### 3.2 How the URL is configured

The API URL is controlled by `desktop/config.py` in this priority order:
1. Environment variable: `set API_URL=http://...` before launching
2. `config.ini` file next to the EXE (users can override it)
3. Hard-coded staging default: `http://108.181.168.43:8000`

`desktop/config.ini` is already updated to point to staging:
```ini
[syntra]
api_url = http://108.181.168.43:8000
```

When you build the EXE, the staging URL is baked into it.

### 3.3 How login and session work after deployment

When a user logs in:
1. App sends `POST /api/login` with email + password
2. Backend verifies password against bcrypt hash in PostgreSQL
3. Backend returns a JSON response with `user_id`, `name`, `role`
4. App stores this in memory (the `self.token` variable in `app.py`)
5. Every screenshot upload / activity log includes the `user_id`

**There is no "session timeout"** in the current implementation — the user stays
logged in until they click Logout or close the app. This is fine for an MVP.

---

## Part 4 — Build the Windows EXE (PyInstaller)

### 4.1 How PyInstaller works internally

PyInstaller solves a fundamental problem: your Python app needs Python installed
to run. Most Windows users don't have Python. PyInstaller bundles:

```
Syntra.exe
  ├── Python interpreter (embedded)
  ├── All your .py files (compiled to .pyc bytecode)
  ├── All pip packages (customtkinter, requests, Pillow, etc.)
  ├── assets/icon.ico
  └── Windows DLLs needed by Python
```

The result is a single `.exe` file that any Windows user can run — **no Python
installation needed.** The tradeoff is the EXE will be ~50-100 MB.

`console=False` in `syntra.spec` means no black terminal window appears — it
looks like a proper Windows app.

### 4.2 One-click build command

```powershell
# Open PowerShell, navigate to project root:
cd d:\CommunityTestAPI\Desktrack\desktop
.\build_exe.ps1
```

What `build_exe.ps1` does:
1. Checks PyInstaller is installed
2. Converts `imgs/app_icon.png` → `assets/icon.ico` (Windows needs .ico format)
3. Cleans old build output
4. Runs `pyinstaller syntra.spec`
5. Reports success + file size

Output: `desktop\dist\Syntra.exe`

**First time only:** install dependencies
```powershell
cd desktop
pip install -r requirements.txt
pip install pyinstaller
```

### 4.3 If the build fails

Common errors and fixes:

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: pynput` | `pip install pynput` |
| `win32api not found` | `pip install pywin32` |
| `customtkinter not found` | `pip install customtkinter` |
| EXE crashes on launch | Run `pyinstaller syntra.spec --debug all` and read the log |
| Missing DLL error | Add the DLL name to `binaries=[]` in syntra.spec |

---

## Part 5 — Create the Installer (Inno Setup)

### 5.1 How Inno Setup works internally

`Syntra.exe` from PyInstaller is just a file — users have to know where to put it.
Inno Setup creates a proper **Windows installer** (`SyntraSetup.exe`) that:

- Shows a professional "Next → Next → Install" wizard
- Copies `Syntra.exe` to `C:\Program Files\Syntra\`
- Creates a Start Menu shortcut
- Creates a Desktop shortcut (optional, user chooses during install)
- Registers in "Add or Remove Programs" (so users can uninstall cleanly)
- Offers to launch the app immediately after install

### 5.2 Build the installer

**Prerequisites:** Download and install Inno Setup from https://jrsoftware.org/isdl.php (free)

```
1. First build the EXE:    .\build_exe.ps1
2. Open Inno Setup Compiler
3. File → Open → select desktop\installer.iss
4. Build → Compile   (or press F9)
5. Output: desktop\installer_output\SyntraSetup.exe
```

### 5.3 What users see when they run SyntraSetup.exe

```
[Welcome screen]      → Next
[License (optional)]  → I accept → Next
[Install folder]      C:\Program Files\Syntra\ → Next
[Select tasks]        ☑ Create desktop shortcut → Next
[Ready to install]    → Install
[Installing...]       Progress bar
[Finished]            ☑ Launch Syntra now → Finish
```

---

## Part 6 — How Users Install and Use the App

### What to give users

Share `SyntraSetup.exe` (from `desktop\installer_output\`).
They can download it from anywhere — Google Drive, your website, direct link.

### What the user does

1. Download `SyntraSetup.exe`
2. Double-click it → click through the wizard → click Finish
3. Syntra opens automatically
4. Type their email + password → Sign In
5. The app starts tracking immediately

### What happens in the background (invisible to user)

- Every 15 seconds: screenshot is captured and uploaded to your staging server
- Continuously: mouse/keyboard activity is tracked and sent every minute
- All data is stored in your MongoDB database under their `user_id`

---

## Part 7 — How App Updates Work

### Current approach (Manual)

When you release a new version:
1. Update the version number in `installer.iss`: `#define MyAppVersion "1.0.1"`
2. Rebuild: `.\build_exe.ps1`
3. Recompile installer in Inno Setup
4. Share the new `SyntraSetup.exe` with users
5. Users download it and run it — Inno Setup detects the old version and upgrades it

Inno Setup handles upgrades automatically because of the `AppId` GUID in `installer.iss`.
When a user runs the new installer, it replaces the old EXE in `Program Files\Syntra\`.

### Auto-update (future improvement, not needed for MVP)

Later you can add an auto-update check inside the Python app:
```python
# On startup, call: GET /api/version
# Compare with current version
# If newer: show "Update available" button that opens the download URL
```

---

## Part 8 — Environment Variables Reference

### Backend `.env` (on the server at `/opt/syntra/backend/.env`)

| Variable | What it does | Example |
|----------|-------------|---------|
| `POSTGRES_URL` | Connection string for PostgreSQL | `postgresql://user:pass@host/db` |
| `MONGODB_URL` | Connection string for MongoDB | `mongodb://user:pass@host:27011/` |
| `MONGODB_DB_NAME` | MongoDB database name | `ai_assistant` |
| `ALLOWED_ORIGINS` | Which URLs can call the API (CORS) | `https://app.vercel.app,http://localhost:3000` |

### Frontend environment (in Vercel Dashboard or `.env.local`)

| Variable | What it does | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Where the frontend sends API calls | `http://108.181.168.43:8000` |

### Desktop app (in `desktop/config.ini` next to the EXE)

| Key | What it does | Default |
|-----|-------------|---------|
| `api_url` | Backend URL the app talks to | `http://108.181.168.43:8000` |

---

## Part 9 — CORS Explained Simply

**CORS (Cross-Origin Resource Sharing)** is a browser security rule that says:

> "A webpage from `vercel.app` is NOT allowed to call an API at `108.181.168.43`
> unless that API explicitly says it's allowed."

Your FastAPI backend reads `ALLOWED_ORIGINS` from `.env` and tells browsers:
"Yes, I accept requests from these URLs."

The desktop app is NOT a browser — it ignores CORS. Only the Next.js frontend
needs to be in `ALLOWED_ORIGINS`.

**Common mistake:** forgetting to add the Vercel URL to `ALLOWED_ORIGINS` after deploying
the frontend. Symptom: the website loads but API calls fail with "CORS error" in DevTools.

**Fix:** Add the URL to `.env` on the server and restart the backend.

---

## Part 10 — Build Commands Cheat Sheet

### Backend (on server)
```bash
# First deploy
./deploy/setup_server.sh
./deploy/deploy_backend.sh

# Every update
ssh root@108.181.168.43
cd /opt/syntra
./deploy/deploy_backend.sh

# View live logs
sudo journalctl -u syntra-backend -f

# Restart manually
sudo systemctl restart syntra-backend
```

### Frontend (Vercel)
```bash
# Just push to GitHub — Vercel auto-deploys
git push origin main

# Or trigger manually in Vercel dashboard → Deployments → Redeploy
```

### Desktop EXE (on your Windows machine)
```powershell
# Install dependencies (first time only)
cd desktop
pip install -r requirements.txt
pip install pyinstaller

# Build EXE
.\build_exe.ps1
# Output: desktop\dist\Syntra.exe

# Build installer (after EXE is built)
# Open Inno Setup → File → Open → installer.iss → Build → Compile
# Output: desktop\installer_output\SyntraSetup.exe
```

---

## Staging Checklist — Before Sharing with Users

- [ ] Backend is running: `http://108.181.168.43/docs` loads
- [ ] PostgreSQL is accessible (backend can connect)
- [ ] MongoDB is accessible (backend can connect)
- [ ] Frontend is deployed on Vercel and loads
- [ ] Login works in the browser (frontend → backend)
- [ ] ALLOWED_ORIGINS includes the Vercel URL
- [ ] `config.ini` points to staging: `api_url = http://108.181.168.43:8000`
- [ ] `.\build_exe.ps1` completes without errors
- [ ] `dist\Syntra.exe` launches and login works
- [ ] Inno Setup compiles `installer.iss`
- [ ] `SyntraSetup.exe` installs cleanly on a test PC
- [ ] After install: app launches, user can log in, screenshots appear in admin panel

---

## Troubleshooting

### Backend won't start
```bash
sudo journalctl -u syntra-backend -n 50
# Look for Python errors — usually a missing .env or wrong database URL
```

### Frontend shows "Network Error"
- Check browser DevTools → Network tab → see the failing request
- Confirm `NEXT_PUBLIC_API_URL` is set correctly in Vercel environment variables
- Confirm backend is running: `http://108.181.168.43:8000/docs`

### Desktop app says "Connection refused"
- Confirm the backend service is running on the server
- Confirm `config.ini` has the right URL
- Check if port 8000 is open in the firewall: `ufw status`

### EXE crashes silently
- Run from PowerShell to see error output:
  ```powershell
  cd "C:\Program Files\Syntra"
  .\Syntra.exe
  ```
- Or rebuild with `console=True` in `syntra.spec` temporarily to see errors

### "CORS error" in browser DevTools
- The Vercel URL is missing from `ALLOWED_ORIGINS` in backend `.env`
- Fix: add it, then `sudo systemctl restart syntra-backend`
