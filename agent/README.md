# 🤖 Marine Graph Agent — POC

Agent LLM (Mistral cloud) qui analyse le **graphe de connaissance Marine** et restitue les résultats en **français orienté décision**.

> Pour le moment, le modèle tourne dans le cloud (API Mistral). À terme, il pourra être migré sur du **Mistral local** (Mistral Small / NeMo en Q4) sans changer l'architecture — seul le client change.

## Architecture

```
┌────────────────┐    HTTP    ┌─────────────────┐    function call    ┌──────────────┐
│  Client (curl, │ ─────────▶ │  FastAPI server │ ──────────────────▶ │ Mistral API  │
│  Python, web)  │            │  (server.py)    │ ◀────────────────── │ (cloud, FR)  │
└────────────────┘            └────────┬────────┘    tool results     └──────────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │   tools.py           │
                            │   • list_top_hubs    │
                            │   • search_attacks   │
                            │   • simulate_attack  │
                            │   • get_proc_impact  │
                            │   • get_asset_detail │
                            │   • get_si_overview  │
                            └──────────────────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │  generalisation/*.csv │
                            └──────────────────────┘
```

**Principe :** le LLM ne touche **jamais** aux DataFrames. Il décide quels outils appeler, lit le JSON renvoyé, et le reformule en français. La couche `tools.py` reste la **source de vérité numérique** — l'agent ne peut pas inventer un chiffre.

## Installation

```bash
cd "/Users/josephw/Desktop/BDD Marine nationale "
pip install -r agent/requirements.txt
```

## Configuration

1. Obtenir une clef API : https://console.mistral.ai/api-keys/
2. Copier le template et renseigner :

```bash
cp agent/.env.example agent/.env
# Éditer agent/.env et coller la clef
```

## Utilisation

### Option A — Test rapide en ligne de commande

```bash
cd "/Users/josephw/Desktop/BDD Marine nationale "
python -m agent.agent "Quels sont les 5 actifs les plus critiques ?"
```

### Option B — Serveur API + clients HTTP

**Démarrer le serveur :**
```bash
cd "/Users/josephw/Desktop/BDD Marine nationale "
uvicorn agent.server:app --reload --port 8000
```

**Swagger UI :** http://localhost:8000/docs

**Exemples curl :**
```bash
# Santé
curl http://localhost:8000/health

# Liste des outils
curl http://localhost:8000/tools | jq

# Question
curl -X POST http://localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"message": "Si CVE-2017-0144 frappe demain, quels processus métier sont en danger ?"}'
```

**Client Python :**
```python
import requests
r = requests.post("http://localhost:8000/query",
                   json={"message": "Détaille l'actif IT-04416"})
print(r.json()["answer"])
```

### Option C — Démo séquentielle (6 questions)

```bash
# Avec serveur lancé sur :8000
python -m agent.demo

# Sans serveur (instancie l'agent en local Python)
python -m agent.demo --direct
```

## Outils exposés au modèle

| Outil | Rôle |
|---|---|
| `get_si_overview()` | Vue d'ensemble chiffrée du SI |
| `list_top_hubs(n)` | Top N actifs critiques (PageRank) |
| `search_attacks(keyword, severity, type)` | Recherche CVE/TTP |
| `simulate_attack_by_id(id, depth)` | Cascade d'impact d'une attaque |
| `get_process_impact(attack_id)` | Impact sur les 15 processus métier |
| `get_asset_details(asset_id)` | Fiche complète d'un actif |

Le modèle décide lui-même lesquels appeler, dans quel ordre, et peut les enchaîner (ex : `search_attacks` → `simulate_attack_by_id` → `get_process_impact`).

## Exemples de questions

- *« Quels sont les 5 actifs les plus critiques de notre SI ? »*
- *« Trouve-moi les CVE critiques liées à Apache ou Log4j »*
- *« Si CVE-2017-0144 frappe demain, combien d'actifs sont touchés et quels processus métier sont en danger ? »*
- *« Compare l'impact de CVE-2017-0144 et CVE-2020-1472. Lequel patcher en priorité ? »*
- *« Pourquoi l'actif IT-04416 est-il considéré comme critique ? »*

## Migration vers Mistral local (étape suivante)

Quand le déploiement local sera prêt :

1. Lancer Ollama avec un modèle compatible : `ollama run mistral-small`
2. Modifier 3 lignes dans `agent.py` :
   ```python
   from openai import OpenAI                       # au lieu de mistralai
   self.client = OpenAI(base_url="http://localhost:11434/v1",
                         api_key="ollama")
   ```
3. L'API Ollama est OpenAI-compatible avec function calling. Tout le reste (tools, server, demo) reste identique.

## Limites assumées du POC

- **Latence** : 2 à 10 s par requête (appel cloud + éventuels multi-tours).
- **Coût** : ~0,001 €/requête sur `mistral-large-latest`.
- **Pas de RAG** : l'agent ne consulte que les outils, pas de base documentaire.
- **Mémoire conversationnelle** : en RAM, partagée entre tous les clients du serveur (utiliser `reset_history: true` ou `POST /reset` pour repartir propre).
- **Audit** : chaque réponse contient la trace `tool_calls` (outils appelés + arguments + résultats) — auditeur peut vérifier qu'aucun chiffre n'a été inventé.
