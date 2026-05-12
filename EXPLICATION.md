# 📘 Explication de l'EDA — Dataset Marine Nationale

## 1. Que représente le dataset ?

Le dossier `neo4j_dataset_50k (1)/` contient un **graphe de cybersécurité** modélisé pour Neo4j. Il simule un système d'information naval **hybride IT/OT** sur une fenêtre de ~14 heures (1ᵉʳ mai 2026, 10h–24h UTC).

### 1.1 Nœuds (entités)

| Fichier | Type de nœud | Volume | Champs clefs |
|---|---|---|---|
| `nodes_assets.csv` | Actif (matériel/logiciel) | **65** | `asset_id`, `type`, `ip`, `role`, `cpe` |
| `nodes_events.csv` | Événement de log | **50 000** | `event_id`, `timestamp`, `event_type`, `status`, `value`, `cve` |
| `nodes_attacks.csv` | Campagne d'attaque | **1** | `attack_id`, `name`, `start_time`, `end_time` |

### 1.2 Relations (arêtes)

| Fichier | Sens | Volume | Sémantique |
|---|---|---|---|
| `rels_dependencies.csv` | asset → asset | 50 | « A dépend de B » (chaîne IT→OT) |
| `rels_generated.csv` | asset → event | 50 000 | « Cet actif a produit cet événement » |
| `rels_targets.csv` | event → asset | 50 000 | « Cet événement vise cet actif » |
| `rels_includes.csv` | attack → event | 10 000 | « Cet événement fait partie de l'attaque » |

### 1.3 Composition du parc

- **30 workstations** (Windows 10) — postes utilisateurs
- **15 servers** (Apache `httpd 2.4.49` — vulnérable !) — `web_server`
- **10 HMI** (Human-Machine Interface) — interfaces opérateurs OT
- **10 PLC** (Programmable Logic Controllers) — automates de terrain

> **Lecture navale :** un bâtiment de la Marine combine exactement ces deux mondes. Les *workstations* sont les postes administratifs / passerelle ; les *PLC* sont les automates qui pilotent moteurs, vannes, capteurs, conduite de tir.

---

## 2. Que fait l'EDA ?

Le notebook `EDA.ipynb` se lit en **3 actes** :

### Acte 1 — Topologie du SI
On reconstitue la chaîne **`Workstation → Server → HMI → PLC`** (modèle Purdue, référence ISA-95 en sécurité industrielle). Cette visualisation matérialise ce qu'on appelle l'**autoroute d'attaque** : un attaquant qui prend un poste utilisateur peut, de proche en proche, atteindre un automate.

### Acte 2 — Caractérisation des événements
- **6 types d'événements** : `file_access`, `http_request`, `login`, `modbus_write`, `read_sensor`, `exploit_attempt`
- **2 statuts** : `normal` (47 554, soit 95,1 %) vs `anomalous` (2 446, soit 4,9 %)
- **100 % des anomalies** sont des `exploit_attempt` exploitant **`CVE-2021-41773`** (Apache HTTP Server — Path Traversal & RCE).
- **Fenêtre d'attaque** : 11h00 → 15h00 UTC, parfaitement visible sur la timeline une fois isolée.

### Acte 3 — Surface d'attaque & propagation
- On joint `events ⨝ targets ⨝ assets` pour identifier **quels actifs sont visés** par les exploits.
- On utilise le graphe `dependencies` pour mesurer combien d'**actifs OT** sont exposés indirectement par un compromis IT.

---

## 3. Pourquoi ces choix ?

| Choix méthodologique | Justification |
|---|---|
| Visualiser le graphe Purdue d'abord | Sans la topologie, les événements sont abstraits. Le graphe rend tangible l'enjeu IT→OT. |
| Croiser `event_type × status` | Permet de voir que **toute** l'anomalie est concentrée sur un seul type (`exploit_attempt`) — ça oriente la modélisation. |
| Tracer la timeline avec la fenêtre d'attaque | Vérifie l'**alignement** des labels (status) avec la vérité-terrain (`ATTACK-001`). C'est notre baseline de validation. |
| Mesurer les actifs OT atteignables | Quantifie le **rayon de souffle** (« blast radius ») d'une compromission — argument central pour le pitch. |

---

## 4. Lien avec les livrables suivants

L'EDA produit les **chiffres factuels** indispensables au *Strategic Pitch* :
- 65 actifs, dont 20 OT critiques
- 4,9 % d'anomalies (4h sur 14h de fenêtre)
- 1 seul CVE responsable → cas d'usage **détection précoce de propagation**
- Modèle graphe natif → ouverture vers **GNN / path scoring** pour le projet final
