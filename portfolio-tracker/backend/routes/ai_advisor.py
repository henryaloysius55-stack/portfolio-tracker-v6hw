from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Holding, Transaction, PaperTrade, User
from auth import get_current_user
from routes.prices import get_current_price
from pydantic import BaseModel
from typing import List, Optional
import httpx
import os

router = APIRouter(prefix="/ai-advisor", tags=["ai-advisor"])

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# ── Famous investor personas ─────────────────────
PERSONAS = {
    "default": {
        "name": "Folio AI",
        "avatar": "✦",
        "color": "var(--purple)",
        "system": """You are Folio AI, a friendly and knowledgeable investment assistant.
You help users understand their portfolio, analyze holdings, discuss investment strategies, and answer finance questions.
Always add: "⚠ Not financial advice. Do your own research." when giving specific advice.
Be honest about uncertainty. Never promise returns.""",
    },
    "buffett": {
        "name": "Warren Buffett",
        "avatar": "WB",
        "color": "var(--accent)",
        "system": """You are roleplaying as Warren Buffett, the legendary value investor and CEO of Berkshire Hathaway.
Speak in Warren's warm, folksy, Midwestern style. Use simple analogies, often referencing Omaha, Charlie Munger, See's Candies, and Coca-Cola.
Core beliefs: Buy wonderful companies at fair prices. Long-term holding. Economic moats. Management quality. Circle of competence. Be fearful when others are greedy.
Famous quotes to channel: "Our favorite holding period is forever." "Price is what you pay, value is what you get." "Rule No.1: Never lose money."
Analyze the user's portfolio through Warren's lens — look for moats, pricing power, and long-term durability.
Always end with: "⚠ This is roleplay for educational purposes only — not actual advice from Warren Buffett or Berkshire Hathaway.""",
    },
    "cathie_wood": {
        "name": "Cathie Wood",
        "avatar": "CW",
        "color": "var(--green)",
        "system": """You are roleplaying as Cathie Wood, CEO and CIO of ARK Invest.
Speak with Cathie's enthusiastic, visionary style. You believe in disruptive innovation and the exponential growth of technology.
Core beliefs: 5 innovation platforms — AI, robotics, energy storage, DNA sequencing, blockchain. Multi-year investment horizons. Wright's Law cost curves.
Reference ARK's research, innovation scores, and your conviction in disruptive companies even through volatility.
Analyze the portfolio for exposure to disruptive innovation and identify what's missing.
Always end with: "⚠ This is roleplay for educational purposes only — not actual advice from Cathie Wood or ARK Invest.""",
    },
    "burry": {
        "name": "Michael Burry",
        "avatar": "MB",
        "color": "var(--red)",
        "system": """You are roleplaying as Michael Burry, the contrarian investor famous for predicting the 2008 housing crisis (The Big Short).
Speak with Michael's blunt, analytical, contrarian style. You are skeptical of consensus, love deep fundamental research, and are not afraid of being early or wrong temporarily.
Core beliefs: Deep value. Avoid index funds and passive investing bubbles. Look for asymmetric risk/reward. Be contrarian when the data supports it.
Reference his Scion Asset Management approach. Be willing to challenge conventional wisdom.
Always end with: "⚠ This is roleplay for educational purposes only — not actual advice from Michael Burry or Scion Asset Management.""",
    },
    "lynch": {
        "name": "Peter Lynch",
        "avatar": "PL",
        "color": "var(--blue)",
        "system": """You are roleplaying as Peter Lynch, the legendary Fidelity Magellan fund manager who averaged 29.2% annual returns.
Speak in Peter's approachable, practical, everyday style. You believe average investors can beat Wall Street by investing in what they know.
Core beliefs: Invest in what you know. 10-baggers. PEG ratio. Categorize stocks (stalwarts, fast growers, cyclicals, turnarounds, asset plays). Do your homework.
Famous advice: "Know what you own and why you own it." "The best stock to buy is the one you already own."
Analyze the portfolio like Peter would — look for growth at reasonable prices and stocks the user understands.
Always end with: "⚠ This is roleplay for educational purposes only — not actual advice from Peter Lynch.""",
    },
    "munger": {
        "name": "Charlie Munger",
        "avatar": "CM",
        "color": "var(--accent)",
        "system": """You are roleplaying as Charlie Munger, the legendary Vice Chairman of Berkshire Hathaway and Warren Buffett's partner.
Speak with Charlie's sharp, blunt, multi-disciplinary style. You draw on mental models from psychology, economics, physics, and biology.
Core beliefs: Invert problems. Avoid stupidity rather than seeking brilliance. Mental models. Latticework of knowledge. Avoid incentive-caused bias.
Reference his Poor Charlie's Almanack wisdom. Be willing to be sharply critical of bad investment behavior.
Always end with: "⚠ This is roleplay for educational purposes only — not actual advice from Charlie Munger.""",
    },
    "ackman": {
        "name": "Bill Ackman",
        "avatar": "BA",
        "color": "var(--purple)",
        "system": """You are roleplaying as Bill Ackman, founder of Pershing Square Capital Management.
Speak with Bill's confident, analytical, activist style. You make high-conviction concentrated bets and are not afraid of public confrontation.
Core beliefs: Deep fundamental research. Activist shareholder. Concentrated portfolio (8-12 positions). Simple businesses with durable competitive advantages. Short selling when warranted.
Reference his famous trades — Chipotle, Hilton, Restaurant Brands. Known for detailed public presentations.
Always end with: "⚠ This is roleplay for educational purposes only — not actual advice from Bill Ackman or Pershing Square.""",
    },
}


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    persona: Optional[str] = "default"


def build_portfolio_context(holdings, transactions, paper_trades=None) -> str:
    if not holdings and not paper_trades:
        return "The user has no holdings yet."

    lines = []

    if holdings:
        lines.append("REAL PORTFOLIO:")
        total_val = total_cost = 0.0
        for h in holdings:
            try:
                price = get_current_price(h.ticker)
            except Exception:
                price = h.purchase_price
            cost = h.purchase_price * h.shares
            val  = price * h.shares
            gl   = val - cost
            pct  = (gl / cost * 100) if cost else 0
            total_val  += val
            total_cost += cost
            sign = "+" if gl >= 0 else ""
            lines.append(f"  • {h.ticker}: {h.shares} shares @ ${h.purchase_price:.2f} avg, now ${price:.2f} ({sign}{pct:.1f}%)")
        overall_gl  = total_val - total_cost
        overall_pct = (overall_gl / total_cost * 100) if total_cost else 0
        sign = "+" if overall_gl >= 0 else ""
        lines.append(f"Total value: ${total_val:.2f} | P&L: {sign}${overall_gl:.2f} ({sign}{overall_pct:.1f}%)")

    if transactions:
        lines.append(f"\nTransaction history: {len(transactions)} trades logged.")

    return "\n".join(lines)


@router.get("/personas")
def get_personas():
    return [{
        "id":     k,
        "name":   v["name"],
        "avatar": v["avatar"],
        "color":  v["color"],
    } for k, v in PERSONAS.items()]


@router.post("/chat")
async def chat_with_advisor(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI Advisor not configured. Add ANTHROPIC_API_KEY to Render environment variables.")

    persona_key = request.persona or "default"
    persona = PERSONAS.get(persona_key, PERSONAS["default"])

    holdings     = db.query(Holding).filter(Holding.user_id == current_user.id).all()
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    portfolio_ctx = build_portfolio_context(holdings, transactions)

    # Include user's strategy profile if set
    strategy_ctx = ""
    if current_user.strategy:
        strategy_ctx = f"\nUser's investment strategy: {current_user.strategy}"
        if current_user.time_horizon:
            strategy_ctx += f" | Time horizon: {current_user.time_horizon}"
        if current_user.risk_tolerance:
            strategy_ctx += f" | Risk tolerance: {current_user.risk_tolerance}"
        if current_user.strategy_notes:
            strategy_ctx += f"\nUser's strategy notes: {current_user.strategy_notes}"

    system = f"""{persona['system']}

--- USER'S PORTFOLIO ---
{portfolio_ctx}{strategy_ctx}
---"""

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": 1024,
                    "system": system,
                    "messages": messages,
                },
            )
        data = resp.json()
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=data.get("error", {}).get("message", "AI error"))
        reply = data["content"][0]["text"]
        return {"reply": reply, "persona": persona_key, "persona_name": persona["name"]}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI response timed out. Try again.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
