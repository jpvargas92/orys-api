from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import time

app = FastAPI()

# Lista de API Keys válidas (por empresa/usuario)
VALID_API_KEYS = {
    "demo123": "Juan Pablo",
    "abc123": "Empresa A",
    "xyz789": "Empresa B"
}

# Middleware para validar API Key
def verify_api_key(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    key = auth.split(" ")[1]
    if key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return key, VALID_API_KEYS[key]

# Modelo de entrada
class PromptRequest(BaseModel):
    prompt: str

class ResponseRequest(BaseModel):
    response: str

# Root
@app.get("/")
def root():
    return {"message": "Orys API running. Use /optimize-input, /optimize-output, /metrics"}

# Endpoint para mostrar la API Key del usuario
@app.get("/my-key")
def get_my_key(request: Request):
    key, user = verify_api_key(request)
    return {"api_key": key, "user": user}

# Optimize Input
@app.post("/optimize-input")
def optimize_input(req: PromptRequest, request: Request):
    key, user = verify_api_key(request)
    optimized = req.prompt[:30]  # Simulación de optimización
    return {
        "user": user,
        "optimized_prompt": optimized,
        "tokens_saved": "38%",
        "latency": "2ms"
    }

# Optimize Output
@app.post("/optimize-output")
def optimize_output(req: ResponseRequest, request: Request):
    key, user = verify_api_key(request)
    optimized = req.response[:50]  # Simulación de optimización
    return {
        "user": user,
        "optimized_response": optimized,
        "tokens_saved": "35%",
        "latency": "3ms"
    }

# Métricas (por ahora globales)
@app.get("/metrics")
def metrics(request: Request):
    key, user = verify_api_key(request)
    return {
        "requests": 10,
        "tokens_saved_avg": "32%",
        "latency_avg": "3ms",
        "cost_savings": "$0.00"
    }

