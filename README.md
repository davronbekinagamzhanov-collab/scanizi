# ScanIZI

Интеллектуальная система анализа товаров и запасов.

## Architecture

The project is composed of:
- **Backend**: FastAPI (Python 3) using async SQLAlchemy, Pydantic, and bcrypt.
- **Frontend**: Next.js 14+ (App Router) using React 19, Recharts, and Lucide React.
- **Database**: PostgreSQL (accessible via Docker or locally).

## Local Setup

### 1. Database & Docker
To run PostgreSQL locally:
```powershell
docker-compose up -d
```
(Or use your own local PostgreSQL instance and update the `.env` files accordingly).

### 2. Backend
Navigate to the `backend` directory, create a virtual environment, and install dependencies:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Set up your `.env` file based on `.env.example`. Make sure `DATABASE_URL` matches your local setup.

Run Alembic migrations to initialize the database schema:
```powershell
alembic upgrade head
```

(Optional) To populate demo data:
```powershell
python seed_db.py
```

Run the FastAPI development server:
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Swagger UI will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 3. Frontend
Navigate to the `frontend` directory and install dependencies:
```powershell
cd frontend
npm install
```

Set up your `.env.local` based on `.env.example`.

Run the Next.js development server:
```powershell
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

## Demo Credentials
If you have seeded the database (`seed_db.py`), you can log in with:
- `admin` / `admin`
- `manager` / `manager`
- `employee` / `employee`

## Environment Variables

**Backend (`backend/.env`)**:
- `DATABASE_URL`: Connection string (asyncpg)
- `DATABASE_URL_SYNC`: Connection string (psycopg2)
- `JWT_SECRET`: Secret key for JWT signing
- `GEMINI_API_KEY`: API key for Gemini Integration (leave empty if unused)
- `FRONTEND_URL`: URL of the frontend (for CORS)

**Frontend (`frontend/.env.local`)**:
- `NEXT_PUBLIC_API_URL`: URL of the backend API

## Deployment Overview
When deploying to a cloud platform (like Render, Vercel, or Heroku):

1. **Database**: Provision a managed PostgreSQL instance.
2. **Backend**: 
   - Set environment variables (`DATABASE_URL`, `JWT_SECRET`, `FRONTEND_URL`, etc.).
   - Migration command: `alembic upgrade head`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. **Frontend**:
   - Set `NEXT_PUBLIC_API_URL` to your production backend URL.
   - Build command: `npm run build`
   - Start command: `npm run start` (or deploy directly to a static hosting/Vercel).
