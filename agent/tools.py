"""Outils du graphe Marine — exposés à l'agent Mistral via function calling.

Chaque fonction renvoie un dict JSON sérialisable. Le LLM ne voit que ces
résultats structurés ; il ne touche jamais aux DataFrames directement.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "generalisation"

# ─── Cache de chargement (lazy + idempotent) ──────────────────────
# Le serveur FastAPI est mono-process : on charge les DataFrames et le graphe
# une seule fois en mémoire au premier appel d'outil, puis tout est servi
# depuis ce cache. Évite de relire 20 000 dépendances à chaque tool call.
_cache: dict = {}


def _load_all():
    if _cache:
        return _cache
    _cache["attacks"] = pd.read_csv(DATA_DIR / "nodes_attacks_final.csv")
    _cache["events"] = pd.read_csv(DATA_DIR / "nodes_events_final.csv",
                                     parse_dates=["timestamp"])
    _cache["processes"] = pd.read_csv(DATA_DIR / "processes_final.csv")
    _cache["dependencies"] = pd.read_csv(DATA_DIR / "rels_dependencies_final.csv")
    _cache["targets"] = pd.read_csv(DATA_DIR / "rels_targets_final.csv")
    _cache["generated"] = pd.read_csv(DATA_DIR / "rels_generated_final.csv")

    G = nx.from_pandas_edgelist(
        _cache["dependencies"], source="source", target="target",
        edge_attr=["weight"], create_using=nx.DiGraph,
    )
    _cache["G"] = G
    _cache["G_rev"] = G.reverse(copy=False)
    _cache["pagerank"] = nx.pagerank(G, weight="weight", alpha=0.85)
    _cache["proc_name"] = _cache["processes"].set_index("id")["name"].to_dict()
    return _cache


# ─── Mappers actif → processus (reproduits du notebook) ────────────
_PROC_DIST = {
    "process-007": 0.28, "process-011": 0.22, "process-015": 0.20,
    "process-012": 0.18, "process-003": 0.18, "process-010": 0.15,
    "process-014": 0.12, "process-001": 0.10, "process-013": 0.10,
    "process-005": 0.08, "process-008": 0.07, "process-006": 0.07,
    "process-002": 0.06, "process-009": 0.05, "process-004": 0.03,
}


def _moa_synth_map(asset_id: str) -> list[str]:
    """Reproduit SyntheticMOAMapper : PageRank → n + distribution-cible.

    Le seed du RNG est dérivé de l'asset_id via MD5 → le mapping est
    DÉTERMINISTE et REPRODUCTIBLE entre runs, ce qui est exigé pour
    l'audit (un même actif sera toujours mappé sur les mêmes processus).
    """
    c = _load_all()
    pct = pd.Series(c["pagerank"]).rank(pct=True).get(asset_id, 0.5)
    if pct > 0.95:
        n = 5
    elif pct > 0.80:
        n = 3
    elif pct > 0.40:
        n = 2
    else:
        n = 1
    rng = np.random.default_rng(int(hashlib.md5(asset_id.encode()).hexdigest()[:8], 16))
    pids = list(_PROC_DIST.keys())
    weights = np.array(list(_PROC_DIST.values()), dtype=float)
    weights /= weights.sum()
    chosen = set()
    tries = 0
    while len(chosen) < n and tries < 30:
        chosen.add(str(rng.choice(pids, p=weights)))
        tries += 1
    return list(chosen)


# ─── Cascade primitive ────────────────────────────────────────────
def _simulate_cascade(seeds, depth=4, threshold=0.1, initial_severity=1.0):
    """BFS pondéré sur le GRAPHE INVERSÉ.

    Les arêtes du graphe sont `A DEPENDS_ON B` → A pointe vers B. Mais
    l'impact remonte DE B VERS A (si B tombe, A est affecté). On parcourt
    donc G.reverse() pour que `successors(node)` renvoie les actifs qui
    DÉPENDENT de `node` — c'est-à-dire ceux que la cascade va frapper.
    """
    c = _load_all()
    G_rev = c["G_rev"]
    severity = {a: initial_severity for a in seeds if a in G_rev}
    reached_at = {a: 0 for a in severity}
    frontier = list(severity.keys())
    for d in range(1, depth + 1):
        nxt = []
        for node in frontier:
            for parent in G_rev.successors(node):
                w = G_rev[node][parent].get("weight", 0.5)
                p = severity[node] * w
                if p < threshold:
                    continue
                if p > severity.get(parent, 0):
                    severity[parent] = p
                    reached_at[parent] = d
                    nxt.append(parent)
        frontier = nxt
        if not frontier:
            break
    return severity, reached_at


# ═══ OUTILS EXPOSÉS À L'AGENT ═══════════════════════════════════════

def list_top_hubs(n: int = 10) -> dict:
    """Top N actifs les plus centraux du SI (PageRank pondéré)."""
    c = _load_all()
    pr = c["pagerank"]
    top = sorted(pr.items(), key=lambda x: -x[1])[:n]
    return {
        "total_assets": c["G"].number_of_nodes(),
        "hubs": [{"asset_id": a, "pagerank": round(s, 6),
                   "in_degree": c["G"].in_degree(a),
                   "out_degree": c["G"].out_degree(a)}
                  for a, s in top],
    }


def search_attacks(keyword: str = "", severity: str = "",
                    attack_type: str = "", limit: int = 10) -> dict:
    """Recherche d'attaques (CVE/TTP) par mot-clé, sévérité, ou type."""
    df = _load_all()["attacks"].copy()
    if keyword:
        m = (df["name"].str.contains(keyword, case=False, na=False)
             | df["description"].str.contains(keyword, case=False, na=False)
             | df["id"].str.contains(keyword, case=False, na=False))
        df = df[m]
    if severity:
        df = df[df["severity"] == severity]
    if attack_type:
        df = df[df["type"] == attack_type]
    df = df.head(limit)
    rows = df[["id", "name", "type", "tactics", "severity", "cvss_score"]].copy()
    rows["cvss_score"] = rows["cvss_score"].fillna("n/a")
    return {
        "total_matches": int(len(df)),
        "matches": rows.to_dict(orient="records"),
    }


def simulate_attack_by_id(attack_id: str, depth: int = 4,
                            threshold: float = 0.1) -> dict:
    """Simule la cascade d'impact d'une attaque (CVE ou TTP) par identifiant."""
    c = _load_all()
    hits = c["targets"][c["targets"]["source"] == attack_id]
    if hits.empty:
        return {"error": f"Aucune cible trouvée pour {attack_id}"}
    seeds = hits["target"].tolist()
    initial_sev = float(hits["impact_score"].max())
    sev, dep = _simulate_cascade(seeds, depth=depth, threshold=threshold,
                                   initial_severity=initial_sev)
    pct = len(sev) / c["G"].number_of_nodes() * 100
    qualif = ("critique" if pct > 20 else
              "préoccupant" if pct > 5 else "limité")
    top_assets = sorted(sev.items(), key=lambda x: -x[1])[:10]
    return {
        "attack_id": attack_id,
        "n_seeds": len(seeds),
        "n_compromised": len(sev),
        "pct_of_si": round(pct, 2),
        "qualification": qualif,
        "max_depth": max(dep.values()) if dep else 0,
        "mean_severity": round(float(np.mean(list(sev.values()))), 3),
        "n_severe": int(sum(1 for v in sev.values() if v >= 0.7)),
        "top_10_compromised": [{"asset": a, "severity": round(s, 3),
                                  "depth": dep[a]}
                                 for a, s in top_assets],
    }


def get_process_impact(attack_id: str, depth: int = 4) -> dict:
    """Calcule l'impact d'une attaque sur les processus métier (mapper MOA-synth)."""
    c = _load_all()
    casc = simulate_attack_by_id(attack_id, depth=depth)
    if "error" in casc:
        return casc
    hits = c["targets"][c["targets"]["source"] == attack_id]
    seeds = hits["target"].tolist()
    initial_sev = float(hits["impact_score"].max())
    sev, _ = _simulate_cascade(seeds, depth=depth, initial_severity=initial_sev)

    # Index inverse processus → actifs (sur le périmètre du graphe)
    proc_total = defaultdict(int)
    all_assets = list(c["G"].nodes())
    for a in all_assets:
        for p in _moa_synth_map(a):
            proc_total[p] += 1

    # Aggrégation
    rows = []
    for asset, s in sev.items():
        for p in _moa_synth_map(asset):
            rows.append((p, s))
    if not rows:
        return {"attack_id": attack_id, "processes_impacted": []}
    df = pd.DataFrame(rows, columns=["process", "severity"])
    agg = df.groupby("process").agg(
        n_assets_hit=("severity", "size"),
        mean_severity=("severity", "mean"),
    ).reset_index()
    agg["total_assets"] = agg["process"].map(proc_total)
    agg["coverage_pct"] = agg["n_assets_hit"] / agg["total_assets"] * 100
    agg["impact_score"] = agg["mean_severity"] * agg["coverage_pct"] / 100
    agg["name"] = agg["process"].map(c["proc_name"])
    agg = agg.sort_values("impact_score", ascending=False).head(8)
    return {
        "attack_id": attack_id,
        "n_compromised_total": casc["n_compromised"],
        "processes_impacted": [
            {"name": r["name"],
             "coverage_pct": round(r["coverage_pct"], 1),
             "mean_severity": round(r["mean_severity"], 3),
             "impact_score": round(r["impact_score"], 4),
             "n_assets_hit": int(r["n_assets_hit"]),
             "total_assets": int(r["total_assets"])}
            for _, r in agg.iterrows()
        ],
    }


def get_si_overview() -> dict:
    """Vue d'ensemble du SI : volumes, types, distribution."""
    c = _load_all()
    G = c["G"]
    return {
        "n_assets": G.number_of_nodes(),
        "n_dependencies": G.number_of_edges(),
        "n_attacks": int(len(c["attacks"])),
        "attacks_by_type": c["attacks"]["type"].value_counts().to_dict(),
        "attacks_by_severity": c["attacks"]["severity"].value_counts().to_dict(),
        "n_events": int(len(c["events"])),
        "events_by_type": c["events"]["type"].value_counts().to_dict(),
        "n_processes": int(len(c["processes"])),
        "process_names": c["processes"]["name"].tolist(),
        "graph_density": round(nx.density(G), 6),
        "n_weakly_connected_components": nx.number_weakly_connected_components(G),
    }


def get_asset_details(asset_id: str) -> dict:
    """Détails d'un actif : PageRank, voisinage, processus métier mappés."""
    c = _load_all()
    G = c["G"]
    if asset_id not in G:
        return {"error": f"Actif {asset_id} introuvable"}
    pr_pct = pd.Series(c["pagerank"]).rank(pct=True).get(asset_id, 0.5)
    procs = [c["proc_name"].get(p, p) for p in _moa_synth_map(asset_id)]
    attacked_by = c["targets"][c["targets"]["target"] == asset_id]["source"].tolist()
    return {
        "asset_id": asset_id,
        "pagerank": round(c["pagerank"][asset_id], 6),
        "pagerank_percentile": round(float(pr_pct), 3),
        "in_degree": int(G.in_degree(asset_id)),
        "out_degree": int(G.out_degree(asset_id)),
        "depends_on": list(G.successors(asset_id))[:10],
        "dependents": list(G.predecessors(asset_id))[:10],
        "mapped_processes": procs,
        "attacked_by": attacked_by[:10],
        "n_attacks_targeting": len(attacked_by),
    }


# ═══ REGISTRE DES OUTILS ════════════════════════════════════════════
TOOLS = {
    "list_top_hubs": list_top_hubs,
    "search_attacks": search_attacks,
    "simulate_attack_by_id": simulate_attack_by_id,
    "get_process_impact": get_process_impact,
    "get_si_overview": get_si_overview,
    "get_asset_details": get_asset_details,
}


# ═══ DESCRIPTIONS JSON SCHEMA (pour Mistral function calling) ═══════
TOOL_DESCRIPTIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_si_overview",
            "description": "Vue d'ensemble chiffrée du système d'information : "
                            "nombre d'actifs, d'attaques, de processus, distribution "
                            "des types et sévérités. À appeler en premier pour cadrer "
                            "une analyse.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_top_hubs",
            "description": "Retourne les N actifs les plus centraux du SI selon "
                            "leur PageRank pondéré. Un actif central est un point de "
                            "défaillance unique potentiel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {"type": "integer",
                           "description": "Nombre d'actifs à retourner (1-50)",
                           "default": 10},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_attacks",
            "description": "Recherche des attaques (CVE ou TTP) par mot-clé, "
                            "sévérité ou type. Utile pour trouver l'identifiant "
                            "d'une attaque avant de la simuler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string",
                                "description": "Mot-clé recherché dans nom ou description "
                                                "(ex: 'Apache', 'Log4Shell', 'SMB')"},
                    "severity": {"type": "string",
                                  "enum": ["critical", "high", "medium", "low"],
                                  "description": "Filtre sur la sévérité"},
                    "attack_type": {"type": "string",
                                     "enum": ["CVE", "TTP"],
                                     "description": "CVE = faille technique précise, "
                                                     "TTP = comportement MITRE ATT&CK"},
                    "limit": {"type": "integer",
                               "description": "Nombre max de résultats",
                               "default": 10},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_attack_by_id",
            "description": "Simule la cascade d'impact d'une attaque (CVE ou TTP) "
                            "et retourne le nombre d'actifs compromis, la "
                            "qualification (limité/préoccupant/critique), la "
                            "sévérité moyenne et le top 10 des actifs touchés.",
            "parameters": {
                "type": "object",
                "properties": {
                    "attack_id": {"type": "string",
                                   "description": "Identifiant exact de l'attaque "
                                                   "(ex: 'CVE-2017-0144', 'T1059')"},
                    "depth": {"type": "integer",
                               "description": "Profondeur max de propagation (1-8)",
                               "default": 4},
                },
                "required": ["attack_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_process_impact",
            "description": "Calcule l'impact d'une attaque sur les 15 processus "
                            "métier de la Marine (Gestion des Flottes, Maintenance "
                            "des Navires, etc.) en utilisant le mapping MOA "
                            "synthétique. Retourne le score d'impact par processus.",
            "parameters": {
                "type": "object",
                "properties": {
                    "attack_id": {"type": "string",
                                   "description": "Identifiant exact de l'attaque"},
                    "depth": {"type": "integer", "default": 4},
                },
                "required": ["attack_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_asset_details",
            "description": "Détails d'un actif spécifique : centralité PageRank, "
                            "ses dépendances et dépendants, processus métier "
                            "supportés, attaques qui le ciblent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_id": {"type": "string",
                                  "description": "Identifiant exact de l'actif "
                                                  "(ex: 'IT-04416')"},
                },
                "required": ["asset_id"],
            },
        },
    },
]
