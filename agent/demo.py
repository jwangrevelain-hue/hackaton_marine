"""Démo : envoie une série de requêtes à l'agent via l'API HTTP.

Prérequis :
    1. Renseigner agent/.env (cf. .env.example)
    2. Démarrer le serveur :  uvicorn agent.server:app --port 8000
    3. Lancer cette démo   :  python -m agent.demo

Mode direct (sans serveur) :
    python -m agent.demo --direct
"""
from __future__ import annotations

import argparse
import sys
import time

QUERIES = [
    "Donne-moi une vue d'ensemble de notre système d'information.",
    "Quels sont les 5 actifs les plus critiques du SI ?",
    "Trouve-moi les CVE critiques liées à Windows ou SMB.",
    "Si CVE-2017-0144 (EternalBlue) frappe demain, combien d'actifs sont touchés "
    "et quels processus métier sont les plus en danger ?",
    "Compare l'impact métier de CVE-2017-0144 et CVE-2020-1472. "
    "Lequel devrions-nous prioriser pour le patching ?",
    "Détaille l'actif IT-04416. Pourquoi est-il considéré comme critique ?",
]


def call_api(url: str, message: str, reset: bool = True) -> dict:
    import requests
    r = requests.post(f"{url}/query",
                       json={"message": message, "reset_history": reset},
                       timeout=120)
    r.raise_for_status()
    return r.json()


def call_direct(message: str, agent) -> dict:
    return agent.query(message)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000",
                    help="URL du serveur (défaut: http://localhost:8000)")
    p.add_argument("--direct", action="store_true",
                    help="Instancier l'agent localement au lieu de passer par le serveur")
    p.add_argument("--limit", type=int, default=len(QUERIES),
                    help="Nombre de questions à exécuter")
    args = p.parse_args()

    agent = None
    if args.direct:
        from .agent import MarineGraphAgent
        agent = MarineGraphAgent()
        print(f"\n📡 Mode direct (modèle = {agent.model})\n")
    else:
        print(f"\n📡 Mode API ({args.url})")
        import requests
        try:
            h = requests.get(f"{args.url}/health", timeout=5).json()
            print(f"   ✅ Agent en ligne — modèle = {h.get('model')}, "
                   f"{h.get('n_tools')} outils\n")
        except Exception as e:
            print(f"   ❌ Serveur injoignable : {e}")
            print(f"   Lance d'abord : uvicorn agent.server:app --port 8000")
            sys.exit(1)

    for i, q in enumerate(QUERIES[:args.limit], 1):
        print("═" * 78)
        print(f"  Q{i}. {q}")
        print("═" * 78)
        t0 = time.time()
        try:
            r = (call_direct(q, agent) if args.direct
                 else call_api(args.url, q))
        except Exception as e:
            print(f"   ❌ {type(e).__name__}: {e}\n")
            continue
        print()
        print(r["answer"])
        print()
        print(f"   ⏱  {r['elapsed_s']}s · {r['n_turns']} tours · "
               f"{len(r['tool_calls'])} appels d'outils :")
        for tc in r["tool_calls"]:
            print(f"        ↪ {tc['name']}({tc['args']})")
        print()


if __name__ == "__main__":
    main()
