# 📂 Explications des données — guide pour débutants

**Public visé :** quelqu'un qui ouvre les CSV pour la première fois et veut comprendre **ce qu'ils contiennent**, **pourquoi ils sont organisés comme ça**, et **quels concepts cyber/métier sont derrière**.

---

## Table des matières

1. [Vue d'ensemble — pourquoi deux datasets ?](#1)
2. [Concepts de base à connaître avant de plonger](#2)
3. [Dataset 1 — `neo4j_dataset_50k` (cas d'école IT/OT)](#3)
4. [Dataset 2 — `generalisation` (cas généralisé)](#4)
5. [Glossaire : CVE, TTP, CVSS, CPE, MITRE…](#5)
6. [Comment lire un fichier ligne par ligne](#6)
7. [Les pièges et trous de la donnée](#7)

---

<a id="1"></a>
## 1. Vue d'ensemble — pourquoi deux datasets ?

On a **deux jeux de données**, à deux niveaux de maturité :

| Dataset | Taille | But pédagogique |
|---|---|---|
| `neo4j_dataset_50k/` | 65 actifs, 50 000 événements, 1 attaque | **Cas d'école** : architecture IT/OT type *navire* avec une attaque scriptée bien identifiée. Sert à comprendre les bases. |
| `generalisation/` | 9 855 actifs, 2 000 événements, 1 000 attaques, 15 processus métier | **Cas généralisé** : graphe plus large et plus dense, beaucoup d'attaques de types variés, ajout de la dimension processus métier. Plus proche d'un vrai SI d'entreprise. |

Les deux suivent le même **modèle graphe** (nœuds + relations), mais le second est plus riche.

> **Métaphore.** Le premier dataset est une *maquette* qu'on peut tenir dans une main pour comprendre la mécanique. Le second est une *vraie cartographie* d'un système d'information complexe.

---

<a id="2"></a>
## 2. Concepts de base à connaître avant de plonger

### 2.1 IT vs OT — la grande différence

- **IT** = *Information Technology*. Ce sont les ordinateurs « classiques » : postes utilisateurs, serveurs web, bases de données, mail, etc. → **monde de la donnée**.
- **OT** = *Operational Technology*. Ce sont les équipements qui pilotent du **physique** : automates (PLC), interfaces de contrôle (HMI), capteurs. → **monde du métal**.

Sur un navire, l'IT c'est la bureautique et la communication ; l'OT c'est ce qui fait tourner les moteurs, ouvrir une vanne, viser un canon. Une attaque IT peut **basculer dans l'OT** par les dépendances entre les deux mondes, et là ça devient dangereux pour la sécurité physique.

### 2.2 Le modèle Purdue

C'est l'architecture standard d'un SI industriel, en couches :

```
   Niveau 4-5 │  IT bureautique          Workstations
              │       ↓
   Niveau 3   │  IT supervision          Servers
              │       ↓
   Niveau 2   │  Postes opérateur OT     HMI  (Human-Machine Interface)
              │       ↓
   Niveau 1   │  Contrôle process        PLC  (Programmable Logic Controller)
              │       ↓
   Niveau 0   │  Capteurs / actionneurs  (vannes, moteurs, capteurs)
```

C'est la **chaîne de dépendance** qu'on retrouvera dans `rels_dependencies.csv` du dataset 1.

### 2.3 Le format graphe Neo4j

Les fichiers CSV sont nommés selon une convention Neo4j (logiciel de base de données graphe) :

- `nodes_XXX.csv` = un type de **nœud** (= un type d'objet).
- `rels_XXX.csv` = un type de **relation** (= un type de lien entre objets).

Les colonnes spéciales `:ID`, `:START_ID`, `:END_ID`, `:TYPE` sont des **annotations Neo4j** pour dire « cette colonne est l'identifiant », « cette colonne est l'origine de la flèche », etc. Si tu lis avec pandas, ce sont des colonnes comme les autres.

---

<a id="3"></a>
## 3. Dataset 1 — `neo4j_dataset_50k` (cas d'école IT/OT)

### 3.1 Vue d'ensemble

```
                     ATTACK-001
                     │       │
            INCLUDES │       │  (pas de TARGETS direct dans ce dataset)
                     ▼       │
              ┌─────────────┐│
              │   EVENT     ├┘
              └──┬────┬─────┘
       GENERATED│    │TARGETS
                │    ▼
              ┌────────┐
              │ ASSET  │ ──DEPENDS_ON──▶ ASSET
              └────────┘   (chaîne Purdue)
```

**4 types de nœuds**, **4 types de relations**.

### 3.2 `nodes_assets.csv` — l'inventaire matériel

**65 lignes.** Une ligne = un équipement physique ou logique du SI.

| Colonne | Signification | Exemple |
|---|---|---|
| `asset_id:ID` | Identifiant unique de l'actif | `IT-WS-01` |
| `type` | Catégorie d'équipement | `workstation`, `server`, `HMI`, `PLC` |
| `ip` | Adresse IP réseau | `10.0.0.1` |
| `role` | Fonction métier de l'équipement | `user_endpoint`, `web_server`, `operator_interface`, `controller` |
| `cpe` | Identifiant standard du **logiciel** installé (format CPE) | `cpe:2.3:o:microsoft:windows_10:22h2:*:*:*:*:*:*:*` |

**Décodage du CPE** (voir glossaire §5) :
- `cpe:2.3` → version du format CPE
- `o` → c'est un *operating system* (vs `a` = application, `h` = hardware)
- `microsoft:windows_10:22h2` → éditeur : produit : version

**Comment c'est composé :**
- 30 workstations (Windows 10 22H2)
- 15 servers (Apache HTTP Server `2.4.49` — vulnérable à `CVE-2021-41773` !)
- 10 HMI (Human-Machine Interface OT)
- 10 PLC (Programmable Logic Controller OT)

### 3.3 `nodes_attacks.csv` — les attaques

**1 ligne.** Il y a une seule attaque dans ce dataset, déclarée et scriptée :

| Colonne | Exemple |
|---|---|
| `attack_id:ID` | `ATTACK-001` |
| `name` | `Large Synthetic Attack` |
| `start_time` | `2026-05-01T11:00:00Z` |
| `end_time` | `2026-05-01T15:00:00Z` |

Donc une attaque de 4h, le 1er mai 2026.

### 3.4 `nodes_events.csv` — les événements/logs

**50 000 lignes.** Chaque ligne est un événement de log du SI sur une fenêtre d'environ 14h.

| Colonne | Signification | Exemples |
|---|---|---|
| `event_id:ID` | Identifiant unique | `EVT-000000` à `EVT-049999` |
| `timestamp` | Horodatage ISO 8601 | `2026-05-01T10:00:00Z` |
| `event_type` | Type d'événement | `login`, `file_access`, `http_request`, `modbus_write`, `read_sensor`, `exploit_attempt` |
| `status` | Normal ou anormal | `normal` (95 %), `anomalous` (5 %) |
| `value` | Valeur numérique (pour Modbus/capteur) | `109`, `102`… |
| `cve` | CVE associée si exploit | `CVE-2021-41773` (Apache path traversal) |

**Lecture clef :** **tous** les événements `anomalous` sont des `exploit_attempt` ciblant `CVE-2021-41773`. Ils s'étalent sur la fenêtre 11h-15h, qui coïncide avec `ATTACK-001`. C'est la **vérité-terrain** de l'attaque.

### 3.5 `rels_dependencies.csv` — la chaîne de dépendance Purdue

**50 lignes.** Une ligne = « l'actif A dépend de l'actif B pour fonctionner ».

| Colonne | Signification |
|---|---|
| `:START_ID` | actif qui dépend |
| `:END_ID` | actif dont on dépend |
| `type:TYPE` | toujours `DEPENDS_ON` |
| `protocol` | protocole utilisé (vide ou `Modbus` pour HMI→PLC) |

La structure forme la chaîne Purdue : Workstation → Server → HMI → PLC.

### 3.6 `rels_generated.csv` — qui produit l'événement ?

**50 000 lignes.** « Cet actif a généré cet événement ». Chaque événement est produit par exactement un actif (celui qui a écrit le log).

| Colonne | Exemple |
|---|---|
| `:START_ID` | `OT-HMI-03` (l'actif source) |
| `:END_ID` | `EVT-000000` (l'événement produit) |
| `:TYPE` | `GENERATED` |

### 3.7 `rels_targets.csv` — qui est visé ?

**50 000 lignes.** « Cet événement cible cet actif ». Pour un événement de login par exemple, c'est la machine sur laquelle on essaie de se logger.

| Colonne | Exemple |
|---|---|
| `:START_ID` | `EVT-000000` |
| `:END_ID` | `IT-WS-12` |
| `:TYPE` | `TARGETS` |

### 3.8 `rels_includes.csv` — quels événements appartiennent à l'attaque ?

**10 000 lignes.** « L'attaque inclut ces événements ». C'est le **label de vérité** — il dit exactement quels événements font partie de l'attaque.

| Colonne | Exemple |
|---|---|
| `:START_ID` | `ATTACK-001` |
| `:END_ID` | `EVT-040000` |
| `:TYPE` | `INCLUDES` |

> **Remarque importante.** Sur les 50 000 événements, seuls 2 446 sont marqués `anomalous`, mais l'attaque en `INCLUDES` 10 000. Donc une partie des événements *inclus dans l'attaque* sont en réalité du trafic normal (artefacts de l'attaque qui passent pour normaux) — c'est subtil et réaliste.

---

<a id="4"></a>
## 4. Dataset 2 — `generalisation` (cas généralisé)

### 4.1 Vue d'ensemble

```
                  ATTACK (CVE ou TTP)
                  │      │
        TARGETS  │      │  GENERATES
                  ▼      ▼
              ┌───────┐  ┌───────┐
              │ ASSET │  │ EVENT │ ←── peut citer plusieurs ASSETS
              └──┬────┘  └───────┘    et plusieurs ATTACKS
                 │                     (colonnes related_*)
                 │ DEPENDS_ON (×20 000)
                 ▼
              ┌───────┐
              │ ASSET │
              └───────┘

      [PROCESS]  ←── orphelin, pas relié dans les fichiers
```

**5 types de nœuds** (asset, attack, event, process — mais asset est implicite, déduit des autres tables), **3 types de relations** explicites.

### 4.2 `nodes_attacks_final.csv` — 1 000 attaques

| Colonne | Signification | Exemples |
|---|---|---|
| `id` | Identifiant unique | `CVE-2017-0144`, `T1059` |
| `name` | Nom lisible | `EternalBlue`, `Command and Scripting Interpreter` |
| `type` | `CVE` ou `TTP` (voir §5) | 507 CVE, 493 TTP |
| `tactics` | Phase MITRE ATT&CK | `initial-access`, `execution`, `lateral-movement`… |
| `description` | Description en clair | `Windows SMB Remote Code Execution Vulnerability.` |
| `severity` | Sévérité globale | `critical`, `high`, `medium` |
| `cvss_score` | Score numérique 0-10 (CVE seulement) | `9.8` |
| `cvss_vector` | Décomposition du score CVSS | `CVSS:3.0/AV:N/AC:L/...` |

**Lecture de la dualité CVE/TTP :**
- Une **CVE** = une faille technique précise dans un logiciel (ex : EternalBlue dans SMB Windows).
- Un **TTP** = une *Technique, Tactique ou Procédure* de la matrice MITRE ATT&CK (ex : T1059 = utiliser un interpréteur de scripts comme PowerShell).

Les deux coexistent ici, ce qui est réaliste — un attaquant exploite une CVE pour entrer, puis utilise des TTP pour bouger.

### 4.3 `nodes_events_final.csv` — 2 000 événements

| Colonne | Signification | Exemples |
|---|---|---|
| `id` | `event-00001` à `event-02000` | |
| `name` | Nom court | `Alerte - 1`, `Panne Système - 3` |
| `type` | Catégorie | `Alerte`, `Incident`, `Attaque Détectée`, `Panne Système`, `Maintenance` |
| `timestamp` | Date/heure | `2025-05-21T05:23:00Z` |
| `severity` | `critical`, `high`, `medium`, `low` | |
| `description` | Texte libre | `Alerte générée: Requête SQL suspecte.` |
| `source` | Outil qui a produit le log | `firewall`, `sysmon`, `apache`, `suricata`, `manual` |
| `related_assets` | Liste d'actifs concernés | `"IT-07863, IT-01323"` |
| `related_attacks` | Liste d'attaques liées | `T1517` ou `CVE-2020-7532` (vide pour les pannes) |

**Différence majeure avec dataset 1 :** ici l'événement contient **directement** les listes d'actifs et d'attaques liés (dans des colonnes texte séparées par virgules). C'est moins normalisé mais plus pratique pour l'analyse.

> Les `Panne Système` et `Maintenance` n'ont **pas** de `related_attacks` — ce sont des événements non-malveillants.

### 4.4 `processes_final.csv` — 15 processus métier

| Colonne | Exemple |
|---|---|
| `id` | `process-001` à `process-015` |
| `name` | `Gestion des Flottes`, `Maintenance des Navires`, `Finance et Comptabilité`… |
| `description` | description courte |

**Limite importante :** ce fichier est **isolé**. Aucune autre table ne pointe vers un `process-XXX`. C'est ce qui motive tout le travail sur les `ProcessMapper` du notebook (cf. `EXPLICATIONS_GRAPHE.md`).

### 4.5 `rels_dependencies_final.csv` — 20 000 dépendances

| Colonne | Signification | Exemple |
|---|---|---|
| `source` | actif qui dépend | `IT-06871` |
| `target` | actif dont on dépend | `IT-09675` |
| `type` | toujours `DEPENDS_ON` | |
| `weight` | poids 0.5 / 0.8 / 1.0 | importance de la dépendance |
| `description` | texte | `L'actif IT-06871 dépend de IT-09675.` |

**Le `weight` est nouveau** par rapport au dataset 1 et change tout : il permet de pondérer la cascade (cf. §3 de `EXPLICATIONS_GRAPHE.md`).

### 4.6 `rels_targets_final.csv` — 3 000 cibles d'attaque

| Colonne | Signification | Exemple |
|---|---|---|
| `source` | l'attaque | `T1955` |
| `target` | l'actif visé | `IT-03923` |
| `type` | `TARGETS` | |
| `impact_score` | gravité 0.5–1.0 | `0.84` |
| `mitigation` | conseil de remédiation | `Isoler IT-03923 et appliquer les correctifs pour T1955.` |

> **Attention.** Le sens est inversé par rapport au dataset 1 ! Ici **attack → asset** (l'attaque cible l'actif), alors que dans le dataset 1 c'était event → asset (l'événement vise l'actif). Les colonnes `source`/`target` désambiguïsent.

### 4.7 `rels_generated_final.csv` — 2 000 événements générés par attaques

| Colonne | Signification | Exemple |
|---|---|---|
| `source` | l'attaque | `T4230` |
| `target` | l'événement produit | `event-01756` |
| `type` | `GENERATES` | |
| `probability` | probabilité 0.5–1.0 que la chaîne soit correcte | `0.67` |

**Lecture utile :** la `probability` permet de modéliser l'**incertitude** des outils de détection — un événement peut « probablement » être généré par cette attaque, mais on n'en est pas sûr à 100 %.

---

<a id="5"></a>
## 5. Glossaire — CVE, TTP, CVSS, CPE, MITRE…

### CVE — Common Vulnerabilities and Exposures
Identifiant **public** d'une faille de sécurité dans un logiciel. Format : `CVE-AAAA-NNNNN`.

Exemples qu'on trouve dans la base :
- `CVE-2017-0144` = **EternalBlue** (faille SMB Windows exploitée par WannaCry en 2017).
- `CVE-2021-41773` = faille de path traversal dans Apache HTTP Server 2.4.49.
- `CVE-2021-44228` = **Log4Shell** (faille Log4j de décembre 2021).
- `CVE-2020-1472` = **ZeroLogon** (élévation de privilèges Active Directory).

Le référentiel public est sur https://nvd.nist.gov/.

### TTP — Tactic, Technique, Procedure
Ce sont des **comportements d'attaquants**, catalogués par le **framework MITRE ATT&CK**. Format des identifiants : `TXXXX` (ex : `T1059`).

- **Tactic** = *objectif* haut niveau (ex : « rentrer dans le réseau » = `initial-access`).
- **Technique** = *façon* de réaliser cet objectif (ex : `T1078` = utiliser des comptes valides).
- **Procedure** = *implémentation concrète* (ex : « utiliser un compte volé via phishing »).

La différence avec une CVE : une CVE est une **faille technique précise** (« il y a un bug dans Apache 2.4.49 ») ; un TTP est un **comportement** (« l'attaquant utilise un interpréteur de scripts »).

### CVSS — Common Vulnerability Scoring System
Score numérique 0-10 qui mesure la **gravité** d'une CVE. Plus c'est haut, plus c'est grave.

Le **vector** (ex : `CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`) décrit les **détails** :
- `AV:N` = Attack Vector Network (attaquable à distance)
- `AC:L` = Attack Complexity Low (facile à exploiter)
- `PR:N` = Privileges Required None (pas besoin d'être logué)
- `UI:N` = User Interaction None (pas besoin que la victime clique)
- `C:H / I:H / A:H` = impact High sur Confidentialité, Intégrité, Availability.

Un score 9.8 (`Critical`) signifie en général : exploit facile, à distance, sans authentification, avec impact total.

### CPE — Common Platform Enumeration
Format standard pour **identifier un logiciel/produit** de manière non-ambiguë. Format :

```
cpe:2.3:<part>:<vendor>:<product>:<version>:<update>:<edition>:...
```

- `part` : `a` = application, `o` = operating system, `h` = hardware
- `vendor:product:version` : éditeur, produit, version

Exemple : `cpe:2.3:o:microsoft:windows_10:22h2:*:*:*:*:*:*:*` = Windows 10 22H2.

**Pourquoi c'est utile :** quand une CVE est publiée, elle est associée à un ou plusieurs CPE. Si ton actif a le bon CPE, tu sais qu'il est vulnérable.

### MITRE ATT&CK
Référentiel public (https://attack.mitre.org) qui catalogue **comment les attaquants opèrent**. Organisé en **tactics** (objectifs) et **techniques** (méthodes). Sert dans la base via la colonne `tactics`.

### IT vs OT
Voir §2.1. **IT** = monde de la donnée. **OT** = monde du physique (industriel).

### Modèle Purdue
Voir §2.2. Architecture en couches d'un SI industriel : bureautique → supervision → contrôle → terrain.

### IDS / SIEM / SOC
- **IDS** (Intrusion Detection System) : sonde qui regarde le trafic réseau et lève des alertes (ex : Suricata, qu'on retrouve dans la colonne `source` des événements).
- **SIEM** (Security Information & Event Management) : agrégateur qui collecte tous les logs et corrèle (ex : Splunk, Sekoia).
- **SOC** (Security Operations Center) : l'équipe humaine qui surveille le SIEM 24/7.

---

<a id="6"></a>
## 6. Comment lire un fichier ligne par ligne

### Exemple 1 — décoder une ligne d'asset (dataset 1)

```csv
IT-WS-01,workstation,10.0.0.1,user_endpoint,cpe:2.3:o:microsoft:windows_10:22h2:*:*:*:*:*:*:*
```

Ça se lit : *« l'actif `IT-WS-01` est une **workstation**, à l'IP `10.0.0.1`, c'est un **poste utilisateur** qui tourne sous **Windows 10 22H2**. »*

### Exemple 2 — décoder une ligne d'événement (dataset 1)

```csv
EVT-040000,2026-05-01T11:00:00Z,exploit_attempt,anomalous,,CVE-2021-41773
```

*« L'événement `EVT-040000` s'est produit le 1er mai 2026 à 11h00 UTC. C'est une **tentative d'exploit**, marquée **anormale**. Pas de valeur Modbus associée (champ vide). L'exploit visait la CVE `CVE-2021-41773` (Apache path traversal). »*

### Exemple 3 — décoder une attaque CVE (dataset 2)

```csv
CVE-2017-0144,EternalBlue,CVE,initial-access,Windows SMB Remote Code Execution Vulnerability.,critical,9.8,CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
```

*« `CVE-2017-0144` (alias **EternalBlue**) est une CVE de la phase **initial-access** : une faille d'exécution de code à distance dans le protocole SMB de Windows. Sévérité **critique** (score CVSS **9.8**), exploitable à distance sans authentification ni interaction utilisateur. »*

### Exemple 4 — décoder une attaque TTP (dataset 2)

```csv
T1059,Command and Scripting Interpreter,TTP,execution,"Adversaries may abuse command and scripting interpreters to execute commands, scripts, or binaries.",high,,
```

*« `T1059` est un **TTP** de la matrice MITRE ATT&CK, phase **execution**. Les adversaires abusent des interpréteurs de commandes (PowerShell, Bash, cmd) pour exécuter du code. Sévérité **high**. Pas de score CVSS (les TTP n'en ont pas). »*

### Exemple 5 — décoder un événement complexe (dataset 2)

```csv
event-00001,Alerte - 1,Alerte,2025-05-21T05:23:00Z,critical,Alerte générée: Requête SQL suspecte.,firewall,"IT-07863, IT-01323",T1517
```

*« Le 21 mai 2025 à 5h23, le **firewall** a généré une alerte critique « Requête SQL suspecte ». Deux actifs concernés : **IT-07863** et **IT-01323**. L'attaque liée est `T1517` (un TTP MITRE). »*

---

<a id="7"></a>
## 7. Les pièges et trous de la donnée

À garder en tête en travaillant avec ces fichiers :

### 7.1 Processus métier orphelins (dataset 2)
La table `processes_final.csv` n'est reliée à **aucune autre**. C'est intentionnel : la cartographie SI ↔ métier est en général portée par la MOA et non par les outils techniques. Il faut donc la simuler (cf. les 4 `ProcessMapper` du notebook).

### 7.2 Convention de sens des relations
- Dans le **dataset 1** : `rels_targets` est `event → asset` (l'événement vise l'actif).
- Dans le **dataset 2** : `rels_targets_final` est `attack → asset` (l'attaque vise l'actif).

Faire attention à ne pas mélanger les deux quand on code.

### 7.3 Sévérité libre dans `nodes_attacks_final.csv`
La colonne `severity` contient principalement `critical`/`high`/`medium`, **mais aussi quelques valeurs étranges** (artefacts de parsing CSV — un commentaire qui contient une virgule a fait déborder une ligne). En pratique on filtre ou on fait un fallback `medium`.

### 7.4 Tactics multiples
La colonne `tactics` peut contenir **plusieurs valeurs séparées par virgules**, ex : `"persistence, privilege-escalation"`. Il faut donc parser cette colonne avant de chercher par tactic.

### 7.5 `related_assets` / `related_attacks` sont des **listes texte**
Format : `"IT-07863, IT-01323"`. Il faut `split(",")` et `strip()`. Si la cellule est vide → valeur `NaN` en pandas.

### 7.6 Tous les actifs ne sont pas dans `dependencies`
Certains actifs apparaissent uniquement dans `targets` (cible d'une attaque mais sans dépendance). On reconstruit la liste complète comme :
```python
assets = set(dependencies["source"]) | set(dependencies["target"]) | set(targets["target"])
```

### 7.7 Timestamps en UTC
Tous les timestamps sont en **UTC** (suffixe `Z`). Bien passer `parse_dates=["timestamp"]` à `pd.read_csv()` pour les manipuler correctement.

---

## TL;DR — ce qu'il faut retenir

1. **Deux datasets** : un petit cas d'école IT/OT (dataset 1, 65 actifs) et un grand cas généralisé (dataset 2, 9 855 actifs + processus métier).
2. **Modèle graphe** : tout est nœuds + relations, façon Neo4j.
3. **CVE vs TTP** : une CVE est une *faille précise*, un TTP est un *comportement d'attaquant* (matrice MITRE).
4. **Le dataset 2 ajoute** : pondération des dépendances, multi-attaques, événements à liens flexibles, et processus métier (mais orphelins → à mapper).
5. **Pièges** : sens des relations qui change entre datasets, listes texte à parser, processus orphelins, quelques valeurs aberrantes en `severity`.

Pour comprendre **ce qu'on fait avec ces données**, lire ensuite `EXPLICATIONS_GRAPHE.md`.
