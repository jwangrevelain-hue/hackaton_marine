# 📊 Diagrammes — Démarche projet

Deux schémas Mermaid retraçant (1) la première session de travail — du dataset brut à l'agent POC — et (2) la trajectoire de migration du POC vers la version finale.

> GitHub rend Mermaid nativement dans les fichiers `.md`. Les blocs ci-dessous sont donc directement visibles sur la page du repo.

---

## 1. Session de réflexion — du graphe aux outils, jusqu'à l'agent

```mermaid
flowchart TD
    subgraph S1["① Réflexion & cadrage"]
        A1["Dataset brut<br/>neo4j_dataset_50k/"]
        A2["EDA — EDA.ipynb<br/>topologie Purdue<br/>IT → OT"]
        A3["Hypothèse métier<br/>« blast radius » d'un CVE<br/>sur les processus navals"]
        A1 --> A2 --> A3
    end

    subgraph S2["② Construction du graphe de connaissance"]
        B1["Nœuds<br/>assets · events · attacks · processes"]
        B2["Relations<br/>dependencies · generated · targets"]
        B3["CSV consolidés<br/>generalisation/*.csv"]
        B1 --> B3
        B2 --> B3
    end

    subgraph S3["③ Couche outils — tools.py"]
        C1["get_si_overview()"]
        C2["list_top_hubs(n)<br/>PageRank"]
        C3["search_attacks(kw, sev, type)"]
        C4["simulate_attack_by_id(id, depth)"]
        C5["get_process_impact(attack_id)"]
        C6["get_asset_details(asset_id)"]
    end

    subgraph S4["④ Agent LLM"]
        D1["agent.py<br/>Mistral cloud<br/>+ function calling"]
        D2["server.py<br/>FastAPI · /query · /tools · /health"]
        D3["Réponse FR<br/>orientée décision<br/>+ trace tool_calls auditée"]
        D1 --> D2 --> D3
    end

    A3 --> B1
    A3 --> B2
    B3 --> C1
    B3 --> C2
    B3 --> C3
    B3 --> C4
    B3 --> C5
    B3 --> C6
    C1 --> D1
    C2 --> D1
    C3 --> D1
    C4 --> D1
    C5 --> D1
    C6 --> D1

    classDef phase fill:#0b3d62,stroke:#0a2540,color:#fff,font-weight:bold
    classDef data fill:#e8f1fb,stroke:#0b3d62,color:#0a2540
    classDef tool fill:#fff4e0,stroke:#b8860b,color:#5a3e00
    classDef agent fill:#e9f7ec,stroke:#2e7d32,color:#1b3a1f
    class A1,A2,A3 data
    class B1,B2,B3 data
    class C1,C2,C3,C4,C5,C6 tool
    class D1,D2,D3 agent
```

**Lecture rapide**

1. L'**EDA** dégage le motif d'attaque IT → OT et oriente le besoin métier.
2. Le **graphe** est consolidé en CSV (nœuds + relations) — source de vérité unique.
3. La couche **`tools.py`** expose des fonctions déterministes calculées sur les CSV : le LLM ne touche jamais aux DataFrames.
4. L'**agent** (Mistral + function calling) orchestre les outils, restitue en français, et trace chaque appel pour audit.

---

## 2. Du POC à la version finale

```mermaid
flowchart LR
    subgraph V0["POC actuel"]
        P1["Mistral cloud<br/>(API EU)"]
        P2["FastAPI mono-instance<br/>mémoire RAM partagée"]
        P3["6 tools statiques<br/>sur CSV figés"]
        P4["Pas de RAG<br/>pas de persistance"]
        P5["Auth : aucune"]
    end

    subgraph T["Étapes de durcissement"]
        S1["① Mistral local<br/>Ollama · Q4 · OpenAI-compat<br/>→ souveraineté"]
        S2["② Backend Neo4j live<br/>Cypher au lieu de CSV<br/>→ données fraîches"]
        S3["③ RAG documentaire<br/>doctrines · CTI · ANSSI<br/>→ contexte expert"]
        S4["④ Mémoire par session<br/>Redis / Postgres<br/>→ multi-utilisateurs"]
        S5["⑤ Observabilité<br/>OpenTelemetry · traces · coûts<br/>→ audit Marine"]
        S6["⑥ Auth & RBAC<br/>OIDC + rôles<br/>→ déploiement opérationnel"]
        S7["⑦ Évaluation continue<br/>jeu de questions de référence<br/>→ non-régression LLM"]
    end

    subgraph V1["Version finale"]
        F1["Mistral on-prem<br/>(air-gap possible)"]
        F2["FastAPI scalable<br/>derrière reverse-proxy"]
        F3["Tools branchés Neo4j<br/>+ RAG hybride"]
        F4["Sessions persistées<br/>par utilisateur"]
        F5["Traces auditables<br/>+ métriques temps réel"]
    end

    P1 --> S1 --> F1
    P3 --> S2 --> F3
    P4 --> S3 --> F3
    P2 --> S4 --> F4
    P5 --> S6 --> F2
    S5 --> F5
    S7 --> F5

    classDef poc fill:#fdecea,stroke:#b71c1c,color:#5a0f0f
    classDef step fill:#fff8e1,stroke:#b8860b,color:#5a3e00
    classDef final fill:#e8f5e9,stroke:#2e7d32,color:#1b3a1f
    class P1,P2,P3,P4,P5 poc
    class S1,S2,S3,S4,S5,S6,S7 step
    class F1,F2,F3,F4,F5 final
```

**Ce que chaque étape débloque**

| # | Étape | Gain principal |
|---|---|---|
| ① | Mistral local (Ollama) | Souveraineté, zéro fuite réseau, latence maîtrisée |
| ② | Backend Neo4j live | Le graphe évolue, les outils suivent en Cypher |
| ③ | RAG documentaire | L'agent cite des doctrines / CTI réels, pas seulement des chiffres |
| ④ | Mémoire par session | Plusieurs analystes travaillent en parallèle sans collisions |
| ⑤ | Observabilité | Coût/latence/qualité mesurés en continu |
| ⑥ | Auth & RBAC | Déploiement réaliste sur SI Marine |
| ⑦ | Évaluation continue | Détection immédiate de régression sur changement de modèle |

> L'architecture du POC est volontairement modulaire : chaque étape touche **une seule couche** (client LLM, source de données, orchestration, etc.) sans réécrire l'ensemble.
