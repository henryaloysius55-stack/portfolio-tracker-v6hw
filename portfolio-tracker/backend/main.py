from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes.auth import router as auth_router
from routes.holdings import router as holdings_router
from routes.transactions import router as transactions_router
from routes.benchmark import router as benchmark_router
from routes.watchlist import router as watchlist_router
from routes.news import router as news_router
from routes.insider import router as insider_router
from routes.copytrading import router as copytrading_router
from routes.ai_advisor import router as ai_advisor_router
from routes.paper_trading import router as paper_trading_router
from routes.strategies import router as strategies_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Folio Portfolio Tracker API", version="5.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/")
def root():
    return {"message": "Folio API v5 is running ✅"}

@app.get("/health")
def health():
    return {"status": "ok"}
