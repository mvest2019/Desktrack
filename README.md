# 🤖 AI Assistant — Complete Setup Guide

## Architecture (from SRS §4.1)

```
┌─────────────────────────────────────────────────┐
│              AI Assistant System                │
├──────────────────┬──────────────────────────────┤
│   PostgreSQL     │         MongoDB              │
│   (users table)  │   (raw_samples collection)   │
│                  │                              │
│  • id            │  • _id (ObjectId)            │
│  • username      │  • user_id  ←── links to PG  │
│  • email         │  • filename                  │
│  • password hash │  • image_data (base64)       │
│  • isactive      │  • file_size                 │
│  • created_at    │  • taken_at                  │
└──────────────────┴──────────────────────────────┘
        ↑                      ↑
   Auth / Login          Screenshots / Telemetry
```

**Why two databases?**
- **PostgreSQL** = structured, relational data (users, accounts) — consistent, ACID
- **MongoDB** = unstructured telemetry (screenshots, large docs) — flexible, fast writes at scale

---

## 📦 Project Structure

```
ai-assistant/
├── backend/
│   ├── main.py         ← All API endpoints (login + screenshots)
│   ├── database.py     ← PostgreSQL connection (SQLAlchemy)
│   ├── mongo.py        ← MongoDB connection (pymongo)
│   ├── models.py       ← PostgreSQL table definitions
│   ├── schemas.py      ← Pydantic request/response schemas
│   ├── setup.sql       ← Run this in PostgreSQL first
│   ├── requirements.txt
│   └── .env.example    ← Copy → .env and fill in your credentials
│
├── frontend/
│   ├── pages/
│   │   ├── index.js     ← Login page
│   │   ├── register.js  ← Create account
│   │   └── dashboard.js ← View screenshots
│   ├── styles/
│   └── package.json
│
├── desktop/
│   ├── app.py           ← Windows desktop app (login + screenshot capture)
│   └── requirements.txt
│
└── README.md
```

---

## 🛠 Prerequisites

| Tool | Download | Used for |
|---|---|---|
| Python 3.10+ | python.org | Backend + Desktop app |
| Node.js 18+ | nodejs.org | Next.js frontend |
| PostgreSQL 15+ | postgresql.org | Users / auth |
| MongoDB 7+ | mongodb.com/try/download | Screenshots storage |

---

## STEP 1 — PostgreSQL Setup

```bash
# Open psql or pgAdmin and run:
CREATE DATABASE ai_assistant;
```

Then run `backend/setup.sql` to create the `users` table.

```sql
-- This is what setup.sql creates:
CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    username   VARCHAR(100) NOT NULL,
    email      VARCHAR(255) NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL,
    isactive   BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## STEP 2 — MongoDB Setup

MongoDB does **not** need a schema created manually.
When the first screenshot is uploaded, MongoDB automatically creates:
- Database: `ai_assistant`
- Collection: `raw_samples`

Just make sure MongoDB is running:
```bash
# Windows: Start "MongoDB" from Services
# Or run: net start MongoDB

# Mac: brew services start mongodb-community
```

**Using MongoDB Atlas (cloud)?**
Just paste your connection string in the `.env` file:
```
MONGO_URL=mongodb+srv://youruser:yourpassword@cluster.mongodb.net
```

---

## STEP 3 — Backend Setup

```bash
cd ai-assistant/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install packages (includes pymongo for MongoDB)
pip install -r requirements.txt

# Create .env file
copy .env.example .env
# Now edit .env — fill in your PostgreSQL and MongoDB credentials
```

Your `.env` file should look like:
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/ai_assistant
MONGO_URL=mongodb://localhost:27017
MONGO_DB=ai_assistant
```

```bash
# Start the backend
uvicorn main:app --reload --port 8000
```

Visit **http://localhost:8000/docs** — you'll see all endpoints organized by database.

---

## STEP 4 — Frontend Setup

```bash
cd ai-assistant/frontend
npm install
npm run dev
```

Open **http://localhost:3000**

---

## STEP 5 — Desktop App Setup

```bash
cd ai-assistant/desktop
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

---

## STEP 6 — Create Your Account

Go to **http://localhost:3000/register** and sign up.
Or use the API docs at **http://localhost:8000/docs** → POST /api/register.

---

## Data Flow

```
Desktop App
    │
    │ 1. Email + password entered
    ↓
FastAPI → PostgreSQL
    │ 2. users table checked
    │ 3. bcrypt password verified
    │ 4. Returns user_id, username
    ↓
Desktop App (login success)
    │
    │ 5. Takes screenshot every 15 seconds (pyautogui)
    │ 6. Converts PNG → base64 string
    │ 7. POST /api/screenshots/upload
    ↓
FastAPI → MongoDB
    │ 8. Inserts document into raw_samples collection
    │    { user_id, filename, image_data, file_size, taken_at }
    │ 9. Returns MongoDB ObjectId as confirmation
    ↓
Next.js Dashboard
    10. GET /api/screenshots/{user_id}  → list (no image_data)
    11. Click screenshot → GET /api/screenshots/{id}/image → show image
```

---

## MongoDB Document Example

When a screenshot is saved, this is what it looks like in MongoDB:

```json
{
  "_id": "6639a1b2c4f5e8d9a3b1c2d3",
  "user_id": 1,
  "filename": "screenshot_1_20260507_101500.png",
  "image_data": "iVBORw0KGgoAAAANSUhEUg...(very long base64 string)",
  "file_size": 312450,
  "taken_at": "2026-05-07T10:15:00.000Z"
}
```

---

## Verifying Both Databases

After running the app and logging in, check:

**PostgreSQL** (users):
```sql
SELECT id, username, email, isactive FROM users;
```

**MongoDB** (screenshots):
```javascript
// In MongoDB Compass or mongosh:
use ai_assistant
db.raw_samples.find({}, { image_data: 0 }).sort({ taken_at: -1 }).limit(5)
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `pymongo.errors.ConnectionFailure` | MongoDB is not running. Start the MongoDB service. |
| `psycopg2.OperationalError` | PostgreSQL is not running, or wrong password in .env |
| `Cannot connect to server` (desktop app) | Backend is not running. Run `uvicorn main:app --reload` |
| `Invalid email or password` | Create an account first at localhost:3000/register |
| Screenshots not showing in dashboard | Wait 15 seconds and refresh. Check desktop app is logged in. |
