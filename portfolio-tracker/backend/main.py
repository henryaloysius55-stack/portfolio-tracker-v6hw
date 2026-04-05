from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes.auth          import router as auth_router
from routes.holdings      import router as holdings_router
from routes.transactions  import router as transactions_router
from routes.benchmark     import router as benchmark_router
from routes.watchlist     import router as watchlist_router
from routes.news          import router as news_router
from routes.insider       import router as insider_router
from routes.copytrading   import router as copytrading_router
from routes.ai_advisor    import router as ai_advisor_router
from routes.paper_trading import router as paper_trading_router
from routes.strategies    import router as strategies_router

# --- Initialization ---
app = FastAPI(
    title="Folio Portfolio Tracker API",
    description="Track, analyze, and grow your portfolio.",
    version="5.0.0",
)

# --- CORS Configuration ---
# This allows your Netlify frontend and local machine to talk to this Render backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://foliotracker.netlify.app",
        "https://folio-tracker-v6.netlify.app" # Added in case your URL changed
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Startup ---
@app.on_event("startup")
def startup_event():
    # This creates the portfolio.db (or Postgres tables) when the server starts
    Base.metadata.create_all(bind=engine)

# --- Router Includes ---
app.include_router(auth_router)
app.include_router(holdings_router)
app.include_router(transactions_router)
app.include_router(benchmark_router)
app.include_router(watchlist_router)
app.include_router(news_router)
app.include_router(insider_router)
app.include_router(copytrading_router)
app.include_router(ai_advisor_router)
app.include_router(paper_trading_router)
app.include_router(strategies_router)

# --- Health Check Endpoints ---
@app.get("/")
def root():
    return {"message": "Folio API v5 is running ✅", "status": "online"}

@app.get("/health")
def health():
    return {"status": "ok"}