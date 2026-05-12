"""MarineGraphAgent — wrapper Mistral cloud via API REST directe (sans SDK).

L'agent reçoit une question en langage naturel, choisit quels outils du
graphe appeler, exécute ces outils, et reformule le résultat en français.

Discipline forte : le modèle n'invente JAMAIS un chiffre — il ne fait que
narrer les sorties JSON des outils. La couche `tools.py` reste la source
de vérité numérique.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from .tools import TOOLS, TOOL_DESCRIPTIONS

# Chargement .env (minimaliste, sans dépendance externe dotenv).
# On n'utilise pas la lib `python-dotenv` ici pour garder l'agent installable
# uniquement avec `requests` — utile pour les déploiements air-gapped où
# limiter les dépendances tierces est exigé.
_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

SYSTEM_PROMPT = """Tu es l'**Agent Marine Graph**, un assistant d'analyse de cybersécurité
pour la Marine Nationale française.

Tu travailles sur un graphe de connaissance comportant :
- 9 800 actifs IT,
- 1 000 attaques (CVE et TTP MITRE ATT&CK),
- 2 000 événements (alertes, incidents, attaques détectées, pannes, maintenances),
- 15 processus métier (Gestion des Flottes, Maintenance des Navires, Sécurité, etc.).

## Mission
Répondre aux questions opérationnelles sur ce graphe en utilisant les outils
fournis, et restituer en français des **briefings concis orientés décision**.

## Règles strictes
1. **NE JAMAIS inventer un chiffre.** Toujours utiliser un outil pour obtenir
   les valeurs numériques. Si l'outil ne renvoie pas une donnée, dire "je ne
   l'ai pas".
2. **Répondre en français**, ton sobre, professionnel, sans jargon non expliqué.
3. **Adapter l'audience** : par défaut, briefing court pour un décideur
   (3 à 6 phrases). Si l'utilisateur précise "pour un analyste", détaille.
4. **Qualifier la sévérité** : <5 % du SI = limité, 5-20 % = préoccupant,
   >20 % = critique.
5. **Enchaîner les outils si nécessaire**. Par exemple : `search_attacks`
   pour trouver l'ID, puis `simulate_attack_by_id`, puis `get_process_impact`.
6. **Quand tu nommes un actif ou un processus, encadrer en gras** (markdown).
7. **Toujours terminer par une recommandation actionnable** quand cela a du sens.
8. **NE JAMAIS inventer le rôle, la fonction, l'OS ou la description d'un actif.**
   Le dataset ne contient PAS de colonne `role` pour les actifs `IT-XXXXX` du
   référentiel `generalisation`. Si un outil ne renvoie pas cette donnée :
   - écrire littéralement « *rôle non renseigné dans le référentiel* », ou
   - décrire l'actif uniquement par ses **métriques objectives** (PageRank,
     in-degree, out-degree, processus mappés, attaques le ciblant).
   ❌ INTERDIT : « **IT-04416** — *Serveur central de supervision* » (inventé)
   ✅ AUTORISÉ : « **IT-04416** — *PageRank 0,000679, 9 dépendants directs,
     rôle non renseigné dans le référentiel* »
9. **Idem pour les CVE/TTP** : ne pas paraphraser leur description si l'outil
   ne te l'a pas renvoyée ; cite uniquement ce que `search_attacks` t'a fourni.

## Format de réponse type
> 📊 **État** : qualification + chiffres clefs.
> 🎯 **Processus en alerte** : noms + couverture %.
> 🛡️ **Actions recommandées** : 2 à 3 puces concrètes."""


class MarineGraphAgent:
    def __init__(self,
                 api_key: str | None = None,
                 model: str | None = None,
                 max_turns: int = 6,
                 timeout: int = 120):
        self.api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "MISTRAL_API_KEY introuvable. Renseigner agent/.env "
                "(voir .env.example) ou exporter la variable.")
        self.model = model or os.environ.get("MISTRAL_MODEL", "mistral-large-latest")
        self.max_turns = max_turns
        self.timeout = timeout
        self.history: list[dict] = []

    def reset(self):
        self.history = []

    def _call_mistral(self, messages: list[dict]) -> dict:
        """Appel HTTP direct à l'API Mistral (chat completions avec tools)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        body = {
            "model": self.model,
            "messages": messages,
            "tools": TOOL_DESCRIPTIONS,
            "tool_choice": "auto",
            # Température basse (0.2) car on veut des réponses
            # reproductibles pour l'audit : un même JSON d'entrée doit
            # produire un briefing quasi-identique d'un run à l'autre.
            "temperature": 0.2,
        }
        r = requests.post(MISTRAL_API_URL, headers=headers, json=body,
                           timeout=self.timeout)
        if r.status_code != 200:
            raise RuntimeError(f"Mistral API {r.status_code}: {r.text[:300]}")
        return r.json()

    def query(self, user_message: str, verbose: bool = False) -> dict[str, Any]:
        """Boucle agentique : envoie la question → exécute les tool_calls
        → relance le modèle jusqu'à réponse finale.

        Le modèle peut enchaîner plusieurs outils (ex: search_attacks puis
        simulate_attack_by_id puis get_process_impact). On limite à
        `max_turns` itérations pour éviter une boucle infinie si le modèle
        ne converge pas.
        """
        t0 = time.time()
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_message})

        tool_calls_log: list[dict] = []

        for turn in range(self.max_turns):
            resp = self._call_mistral(messages)
            msg = resp["choices"][0]["message"]

            tcs = msg.get("tool_calls") or []
            if tcs:
                # Ajoute le message assistant + les résultats des outils
                messages.append({
                    "role": "assistant",
                    "content": msg.get("content") or "",
                    "tool_calls": tcs,
                })
                for tc in tcs:
                    name = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"]["arguments"] or "{}")
                    except Exception:
                        args = {}
                    if verbose:
                        print(f"   ↪ tool: {name}({args})")
                    fn = TOOLS.get(name)
                    if fn is None:
                        result = {"error": f"Outil inconnu : {name}"}
                    else:
                        try:
                            result = fn(**args)
                        except Exception as e:
                            result = {"error": f"{type(e).__name__}: {e}"}
                    tool_calls_log.append({"name": name, "args": args,
                                            "result": result})
                    messages.append({
                        "role": "tool",
                        "name": name,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                        "tool_call_id": tc["id"],
                    })
                continue

            # Pas d'autre tool call → réponse finale
            answer = msg.get("content") or ""
            self.history.append({"role": "user", "content": user_message})
            self.history.append({"role": "assistant", "content": answer})
            return {
                "answer": answer,
                "tool_calls": tool_calls_log,
                "n_turns": turn + 1,
                "elapsed_s": round(time.time() - t0, 2),
                "model": self.model,
            }

        return {
            "answer": f"⚠️ Le modèle n'a pas convergé en {self.max_turns} tours.",
            "tool_calls": tool_calls_log,
            "n_turns": self.max_turns,
            "elapsed_s": round(time.time() - t0, 2),
            "model": self.model,
        }


# CLI rapide
if __name__ == "__main__":
    import sys
    agent = MarineGraphAgent()
    q = " ".join(sys.argv[1:]) or "Donne-moi une vue d'ensemble du SI."
    print(f"\n🛡️  Question : {q}\n")
    r = agent.query(q, verbose=True)
    print("\n" + "─" * 70)
    print(r["answer"])
    print("─" * 70)
    print(f"({r['n_turns']} tours · {len(r['tool_calls'])} appels d'outils · "
          f"{r['elapsed_s']}s · {r['model']})")
