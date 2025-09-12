# main.py
import os
import time
import sqlite3
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

DB_PATH = "orys.db"
API_KEY_ENV = os.getenv("ORYS_API_KEY", "demo123")  # Cambia en deploy a un valor seguro

app = FastAPI(title="Orys API MVP")

# --- DB init (SQLite simple for MVP) ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint TEXT,
        prompt TEXT,
        optimized TEXT,
        tokens_saved_percent INTEGER,
        latency_ms INTEGER,
        created_at TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# --- Helpers ---
def check_api_key(auth_header: Optional[str]):
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = auth_header.split(" ", 1)[1].strip()
    if token != API_KEY_ENV:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True

def simple_optimize_text(text: str) -> (str, int):
    # Simple heuristic optimizer for MVP:
    # - normalize whitespace
    # - keep most meaningful words (truncate to ~70% words)
    if not text:
        return "", 0
    words = text.strip().split()
    if len(words) <= 6:
        optimized = text.strip()
    else:
        keep = max(1, int(len(words) * 0.7))
        optimized = " ".join(words[:keep])
    # basic cleanup punctuation spacing
    optimized = optimized.replace("  ", " ").strip()
    orig_tokens = max(1, len(words))
    new_tokens = max(1, len(optimized.split()))
    saved_percent = int(round((1 - (new_tokens / orig_tokens)) * 100))
    if saved_percent < 0:
        saved_percent = 0
    return optimized, saved_percent

def log_request(endpoint, prompt, optimized, saved_pct, latency_ms):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO requests (endpoint, prompt, optimized, tokens_saved_percent, latency_ms, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (endpoint, (prompt or "")[:2000], (optimized or "")[:2000], saved_pct, latency_ms, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def aggregate_metrics():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), AVG(tokens_saved_percent), AVG(latency_ms) FROM requests")
    row = c.fetchone()
    conn.close()
    if not row:
        return {"requests": 0, "tokens_saved_avg": "0%", "latency_avg": "0ms", "cost_savings": "$0"}
    total_requests = int(row[0] or 0)
    avg_saved = int(round(row[1] or 0))
    avg_latency = int(round(row[2] or 0))
    # Very rough USD estimate: assume 1 token ~ $0.000002 (toy value) and average tokens per request ≈ 100
    est_token_cost = 0.000002
    avg_tokens_per_request = 100
    est_savings_usd = total_requests * avg_tokens_per_request * (avg_saved/100) * est_token_cost
    return {
        "requests": total_requests,
        "tokens_saved_avg": f"{avg_saved}%",
        "latency_avg": f"{avg_latency}ms",
        "cost_savings": f"${est_savings_usd:.2f}"
    }

# --- Schemas ---
class PromptIn(BaseModel):
    prompt: str

class ResponseOptimizeIn(BaseModel):
    response: str

# --- Endpoints ---
@app.post("/optimize-input")
async def optimize_input(payload: PromptIn, Authorization: Optional[str] = Header(None)):
    check_api_key(Authorization)
    start = time.time()
    optimized, saved_pct = simple_optimize_text(payload.prompt)
    latency_ms = int((time.time() - start) * 1000)
    log_request("/optimize-input", payload.prompt, optimized, saved_pct, latency_ms)
    return JSONResponse({
        "optimized_prompt": optimized,
        "tokens_saved": f"{saved_pct}%",
        "latency": f"{latency_ms}ms"
    })

@app.post("/optimize-output")
async def optimize_output(payload: ResponseOptimizeIn, Authorization: Optional[str] = Header(None)):
    check_api_key(Authorization)
    start = time.time()
    optimized, saved_pct = simple_optimize_text(payload.response)
    latency_ms = int((time.time() - start) * 1000)
    log_request("/optimize-output", payload.response, optimized, saved_pct, latency_ms)
    return JSONResponse({
        "optimized_response": optimized,
        "tokens_saved": f"{saved_pct}%",
        "latency": f"{latency_ms}ms"
    })

@app.get("/metrics")
async def get_metrics(Authorization: Optional[str] = Header(None)):
    check_api_key(Authorization)
    return aggregate_metrics()

@app.get("/")
def root():
    return {"message":"Orys API running. Use /optimize-input, /optimize-output, /metrics"}
