# 📊 Folio — Portfolio Tracker

A full-stack stock portfolio tracker with live prices, charts, and gain/loss tracking.

---

## Stack
- **Backend**: Python + FastAPI + SQLite + yfinance
- **Frontend**: Vanilla HTML/CSS/JS + Chart.js

---

## Quick Start

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

API will be live at: http://localhost:8000
Interactive docs at: http://localhost:8000/docs

### 2. Frontend Setup

No build step needed. Just open the frontend in a browser:

```bash
cd frontend
# Option A: Python simple server
python -m http.server 3000

# Option B: VS Code Live Server extension
# Right-click index.html → Open with Live Server
```

Then visit: http://localhost:3000

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/holdings/` | All holdings with live prices |
| POST | `/holdings/` | Add a new holding |
| PATCH | `/holdings/{id}` | Update a holding |
| DELETE | `/holdings/{id}` | Delete a holding |
| GET | `/holdings/validate/{ticker}` | Validate a ticker symbol |

---

## Project Structure

```
portfolio-tracker/
├── backend/
│   ├── main.py          # FastAPI app + CORS
│   ├── database.py      # SQLite connection
│   ├── models.py        # SQLAlchemy ORM models
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── requirements.txt
│   └── routes/
│       ├── holdings.py  # CRUD endpoints
│       └── prices.py    # yfinance price fetching + cache
│
└── frontend/
    ├── index.html       # App shell + all views
    ├── style.css        # Design system + layout
    └── app.js           # API calls, rendering, charts
```

---

## Deployment

### Backend → Railway
1. Push to GitHub
2. Connect repo on [railway.app](https://railway.app)
3. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Frontend → Vercel
1. Push `/frontend` to GitHub
2. Import on [vercel.com](https://vercel.com)
3. Update `API` constant in `app.js` to your Railway URL

---

## Features
- ✅ Add/remove stock positions
- ✅ Live prices via yfinance
- ✅ Gain/loss per position + overall
- ✅ Portfolio allocation doughnut chart
- ✅ Performance bar chart
- ✅ Ticker validation before adding
- ✅ Price caching (60s TTL) to avoid rate limits
- ✅ Responsive dark UI

## Roadmap Ideas
- [ ] Transaction history (multiple buys per ticker)
- [ ] Dividend tracking
- [ ] Benchmark vs S&P 500
- [ ] CSV export
- [ ] Email/SMS alerts for price targets
- [ ] Multiple portfolios
