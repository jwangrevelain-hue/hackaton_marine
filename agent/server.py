"""Serveur API FastAPI exposant l'agent en HTTP.

Endpoints :
- POST /query   → envoyer une question, recevoir la réponse + trace
- GET  /health  → vérifie que l'agent est instanciable
- GET  /tools   → liste les outils disponibles
- POST /reset   → vide l'historique conversationnel

Lancer :
    cd "/Users/josephw/Desktop/BDD Marine nationale "
    uvicorn agent.server:app --reload --port 8000

Démo curl :
    curl -X POST http://localhost:8000/query \\
         -H "Content-Type: application/json" \\
         -d '{"message": "Quels sont les 5 actifs les plus critiques ?"}'
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import MarineGraphAgent
from .tools import TOOL_DESCRIPTIONS

app = FastAPI(
    title="Marine Graph Agent API",
    description="POC d'agent LLM (Mistral cloud) pour l'analyse du graphe Marine",
    version="0.1.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                    allow_methods=["*"], allow_headers=["*"])

# Instance unique partagée (état conversationnel en mémoire)
_agent: MarineGraphAgent | None = None


def get_agent() -> MarineGraphAgent:
    global _agent
    if _agent is None:
        _agent = MarineGraphAgent()
    return _agent


# ─── schémas ──────────────────────────────────────────────────────
class QueryIn(BaseModel):
    message: str = Field(..., description="Question en langage naturel")
    reset_history: bool = Field(False, description="Vider la mémoire avant la question")
    verbose: bool = Field(False, description="Trace des appels d'outils en stdout")


class QueryOut(BaseModel):
    answer: str
    tool_calls: list[dict[str, Any]]
    n_turns: int
    elapsed_s: float
    model: str


# ─── routes ───────────────────────────────────────────────────────
@app.get("/health")
def health():
    try:
        agent = get_agent()
        return {"status": "ok", "model": agent.model,
                "n_tools": len(TOOL_DESCRIPTIONS)}
    except Exception as e:
        raise HTTPException(503, f"Agent indisponible : {e}")


@app.get("/tools")
def list_tools():
    return {
        "n_tools": len(TOOL_DESCRIPTIONS),
        "tools": [
            {"name": t["function"]["name"],
             "description": t["function"]["description"],
             "parameters": list(t["function"]["parameters"].get("properties", {}).keys())}
            for t in TOOL_DESCRIPTIONS
        ],
    }


@app.post("/reset")
def reset_history():
    get_agent().reset()
    return {"status": "history cleared"}


@app.post("/query", response_model=QueryOut)
def query(q: QueryIn):
    agent = get_agent()
    if q.reset_history:
        agent.reset()
    try:
        result = agent.query(q.message, verbose=q.verbose)
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    return result


@app.get("/")
def root():
    return {
        "name": "Marine Graph Agent API",
        "version": "0.1.0",
        "endpoints": ["/health", "/tools", "/query (POST)", "/reset (POST)"],
        "docs": "/docs (Swagger UI)",
    }
