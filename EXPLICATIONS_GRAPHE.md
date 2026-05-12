# 📘 Explications pas-à-pas — Notebook `EDA_GENERALISATION`

**Public visé :** quelqu'un qui n'a jamais manipulé de graphe de connaissance, de cascade, ou de cartographie SI. Tu peux lire ce document **avant** d'ouvrir le notebook.

---

## Table des matières

1. [C'est quoi un graphe de connaissance ?](#1)
2. [Le dataset, en images](#2)
3. [C'est quoi une « cascade » ?](#3)
4. [Comment on programme la cascade — le BFS pondéré](#4)
5. [Le problème : du technique au métier (et pourquoi un `Mapper`)](#5)
6. [Les quatre mappers et leurs compromis](#6)
7. [La kill chain MITRE — comment pensent les vrais attaquants](#7)
8. [Le rejeu temporel et les patchs — le SI qui se répare](#8)
9. [Le dashboard — comment l'utiliser](#9)

---

<a id="1"></a>
## 1. C'est quoi un graphe de connaissance ?

Imagine un dessin où **chaque rond est un objet** et **chaque flèche est une relation entre deux objets**. C'est ça, un graphe.

```
   [IT-WS-01] ──dépend de──▶ [IT-SRV-02] ──dépend de──▶ [OT-HMI-01]
   (poste utilisateur)         (serveur)                  (automate)
```

Un **graphe de connaissance**, c'est juste un graphe où :
- on a **plusieurs types de ronds** (actifs, événements, attaques, processus métier…) ;
- on a **plusieurs types de flèches** (« dépend de », « cible », « génère »…) ;
- on stocke des **propriétés** sur les ronds et les flèches (poids, sévérité, date…).

Dans notre cas, le graphe a quatre types de ronds (les **nœuds**) :

| Type de nœud | Quantité | Exemple |
|---|---|---|
| **Asset** (actif) | 9 855 | `IT-04416` — un poste, un serveur, un automate |
| **Attack** (attaque) | 1 000 | `CVE-2021-44228` (Log4Shell) ou `T1059` (Command Scripting) |
| **Event** (événement) | 2 000 | `event-00001` — une alerte, un incident, une panne |
| **Process** (processus métier) | 15 | `process-007` — *Gestion des Flottes* |

Et trois types de flèches (les **relations**) :

| Type | Sens | Quantité |
|---|---|---|
| **DEPENDS_ON** | asset → asset | 20 000 |
| **TARGETS** | attack → asset | 3 000 |
| **GENERATES** | attack → event | 2 000 |

**Pourquoi un graphe et pas un tableau Excel ?** Parce qu'avec un graphe, on peut poser des questions du genre : *« si je casse cet actif, quels actifs en dépendent à 3 sauts de distance ? »* — impossible à formuler simplement en SQL.

---

<a id="2"></a>
## 2. Le dataset, en images

```
                    ┌─────────────┐
                    │   ATTACK    │  ex: CVE-2021-44228
                    └──┬───────┬──┘
              TARGETS  │       │  GENERATES
                       ▼       ▼
                  ┌────────┐  ┌────────┐
                  │ ASSET  │  │ EVENT  │  ex: event-00001 (alerte)
                  └───┬────┘  └────────┘
                      │
                      │  DEPENDS_ON (× 20 000)
                      ▼
                  ┌────────┐
                  │ ASSET  │  un autre actif
                  └────────┘

         [PROCESS]  ← non rattaché dans les fichiers,
                     d'où le besoin d'un Mapper
```

Les processus métier sont **orphelins** dans la base — c'est précisément ce que notre code corrige en construisant un mapping `actif → processus`.

---

<a id="3"></a>
## 3. C'est quoi une « cascade » ?

Soit une dépendance simple :

```
  IT-A ─dépend de─▶ IT-B ─dépend de─▶ IT-C
```

Si **IT-C tombe** (panne, attaque réussie) :
- IT-B, qui dépend de IT-C, est **affecté** ;
- IT-A, qui dépend de IT-B, est **affecté à son tour**, mais à un degré moindre.

C'est ça une **cascade**. Elle se propage **dans le sens inverse** des flèches `DEPENDS_ON` : l'impact remonte du fournisseur vers ses consommateurs.

### Pourquoi un *degré moindre* à chaque saut ?

Parce que dans la vie réelle, toutes les dépendances ne sont pas vitales. Le dataset l'encode avec un `weight` sur chaque dépendance :
- **1.0** : sans ce fournisseur, je suis mort.
- **0.8** : sans lui, je suis fortement dégradé.
- **0.5** : sans lui, je tourne au ralenti.

À chaque saut, on **multiplie** la sévérité par le poids :

```
  IT-C tombe avec sévérité 1.0
  → IT-B impacté avec sévérité 1.0 × 0.8 = 0.8
  → IT-A impacté avec sévérité 0.8 × 0.5 = 0.4
```

Et si la sévérité passe sous un **seuil** (ex: 0.1), on arrête la propagation.

---

<a id="4"></a>
## 4. Comment on programme la cascade — le BFS pondéré

**BFS = Breadth-First Search** = parcours en largeur. C'est l'algorithme le plus simple pour explorer un graphe niveau par niveau.

L'idée en pseudo-code :

```
1.  On part avec un ensemble de "seeds" = les actifs initialement compromis
2.  Pour chaque profondeur de 1 à `depth_max` :
3.      Pour chaque actif déjà touché :
4.          Pour chaque actif qui dépend de lui :
5.              Calculer la nouvelle sévérité = sévérité_courante × poids
6.              Si la nouvelle sévérité > seuil :
7.                  Marquer le voisin comme touché
8.                  L'ajouter à la frontière du prochain niveau
9.  Renvoyer le dictionnaire { actif: sévérité }
```

C'est exactement ce que fait `simulate_cascade()` dans le notebook (cellule 7).

> **Astuce mentale.** Le graphe `DEPENDS_ON` va « du consommateur vers le fournisseur ». Pour propager l'impact, on inverse les flèches : `G.reverse()`. C'est juste un retournement de carte.

---

<a id="5"></a>
## 5. Le problème : du technique au métier (et pourquoi un `Mapper`)

Une fois la cascade simulée, on sait : *« 312 actifs sont touchés »*. C'est un **chiffre technique**.

Le décideur (l'amiral, le DSI) veut savoir : *« lesquels de mes processus métier sont en danger ? La paie ? La maintenance des navires ? La planification des missions ? »*.

Pour répondre, il faut un **dictionnaire de traduction** :

```
   IT-00010  →  Gestion des Flottes, Maintenance des Navires
   IT-00042  →  Finance et Comptabilité
   IT-00128  →  Ressources Humaines
   ...
```

C'est ce qu'on appelle une **cartographie SI ↔ Métier** (typiquement maintenue par la MOA — Maîtrise d'Ouvrage). Le notebook ne l'a pas (la table `processes_final.csv` est orpheline), donc on en simule plusieurs versions.

### L'idée du `ProcessMapper`

Plutôt qu'avoir une seule version « en dur » du mapping, on définit une **interface** simple :

```python
class ProcessMapper:
    def map_asset(self, asset_id) -> list[str]:
        ...  # retourne la liste des process_ids pour cet actif
```

**Tout ce qui suit dans le notebook (calcul d'impact, dashboard) parle à cette interface.** Donc le jour où on reçoit la vraie cartographie MOA, on écrit 10 lignes de `MOAMapper`, on la branche, **et tout fonctionne sans rien changer ailleurs**.

C'est le principe du **strategy pattern** en informatique : on isole *ce qui change* (ici : la logique de mapping) derrière une interface stable.

---

<a id="6"></a>
## 6. Les quatre mappers et leurs compromis

Le notebook implémente quatre stratégies, de la plus naïve à la plus crédible :

### 6.1 `HashMapper` (§3a) — la **baseline neutre**

> *« Je n'ai aucune info, je mets chaque actif sur 1 à 3 processus, tirés par hash MD5 de l'asset_id. »*

- **Avantage** : reproductible, neutre, pas de biais.
- **Inconvénient** : aucun lien avec la réalité. Sert juste à **valider la mécanique** de la cascade.

### 6.2 `SemanticMapper` (§3b) — le **signal des événements**

> *« Je lis les descriptions d'événements ('Requête SQL suspecte', 'Réseau indisponible'…) et j'utilise des mots-clefs pour deviner les processus. »*

Le dictionnaire est éditable :

```python
KEYWORD_TO_PROCESSES = {
    r"base de données|sql": [process-005, process-006, process-008],
    r"réseau|network":      [process-003, process-012, process-007],
    ...
}
```

- **Avantage** : exploite un signal réel ; un expert métier peut **éditer** le dictionnaire.
- **Inconvénient** : ne couvre que les actifs **cités dans les logs**. Les autres tombent dans un `fallback`.

### 6.3 `SyntheticMOAMapper` (§8a) — la **carto synthétique réaliste**

> *« Je combine la position dans le graphe (les hubs servent plein de processus, les feuilles un seul) + le signal sémantique + une distribution-cible métier (le cœur opérationnel est sur-représenté). »*

Concrètement :
- Top 5 % des actifs (super-hubs PageRank) : **5 processus** (= infra partagée comme un AD, un DNS).
- 80–95 % : **3 processus** (= serveurs multi-applicatifs).
- 40–80 % : **2 processus**.
- Bas du graphe (feuilles) : **1 processus** (= équipement spécialisé).

- **Avantage** : produit une carto **structurellement réaliste**. C'est le plus crédible des trois placeholders pour donner des chiffres opérationnels.
- **Inconvénient** : reste synthétique. Aucun expert métier ne l'a validée.

### 6.4 `MOAMapper` (futur) — la **vraie cartographie**

> *« On lit un CSV `asset_id, process_id` validé par la MOA. Point. »*

```python
class MOAMapper(ProcessMapper):
    def __init__(self, csv_path):
        df = pd.read_csv(csv_path)
        self._m = df.groupby("asset_id")["process_id"].apply(list).to_dict()
    def map_asset(self, asset_id):
        return self._m.get(asset_id, [])
```

Le jour où on récupère cette donnée, on écrit ces 10 lignes et tout le dashboard s'en sert automatiquement.

---

<a id="7"></a>
## 7. La kill chain MITRE — comment pensent les vrais attaquants

**MITRE ATT&CK** est un référentiel public qui décrit comment fonctionnent les cyberattaques **dans la vraie vie**. Il liste des **tactics** (objectifs intermédiaires de l'attaquant) dans un ordre canonique :

```
1.  initial-access          (entrer dans le réseau)
2.  execution               (lancer du code)
3.  persistence             (rester après reboot)
4.  privilege-escalation    (passer admin)
5.  defense-evasion         (échapper aux antivirus)
6.  credential-access       (voler des mots de passe)
7.  discovery               (cartographier le réseau)
8.  lateral-movement        (sauter d'une machine à l'autre)
9.  collection              (rassembler les données)
10. command-and-control     (parler avec le C2)
11. exfiltration            (sortir les données)
12. impact                  (chiffrer / détruire / saboter)
```

Une **attaque réelle enchaîne plusieurs phases**. Notre fichier `nodes_attacks_final.csv` a une colonne `tactics` qui indique à quelle phase chaque CVE/TTP correspond.

### Ce que fait `simulate_attack_chain` (§8b)

1. On choisit un actif de départ (`initial_seed`).
2. Pour chaque phase de la kill chain :
   a. On tire une CVE/TTP de la base qui correspond à cette `tactic`.
   b. On lance une cascade depuis le seed actuel.
   c. **Lateral movement** : le seed de la phase suivante est un actif qu'on vient de compromettre (= l'attaquant pivote).
3. On accumule tous les actifs touchés au fil des phases.

C'est **beaucoup plus réaliste** qu'un exploit isolé : on voit l'attaque **se propager** dans le temps **et** dans le réseau.

---

<a id="8"></a>
## 8. Le rejeu temporel et les patchs — le SI qui se répare

### 8.1 Le rejeu temporel (§6)

Les événements ont un `timestamp`. On peut **rejouer l'histoire** : à la date T, on prend tous les événements hostiles antérieurs à T et on simule la cascade.

Curseur en avant dans le temps → plus d'événements → plus d'actifs touchés.

**Limite :** dans cette version, la courbe **monte tout le temps**. Aucun actif ne se répare jamais — c'est faux.

### 8.2 Les patchs (§8c)

Dans la vraie vie, quand une CVE est découverte, on **applique un correctif** quelques jours/semaines/mois plus tard. La rapidité dépend de la sévérité :

| Sévérité de la CVE | Délai typique de patch |
|---|---|
| `critical` | 30 à 90 jours |
| `high` | 90 à 180 jours |
| `medium` | 180 à 365 jours |
| `low` | 365 à 730 jours |

`generate_patch_schedule()` simule ce calendrier : pour chaque `(asset, attack)`, on tire une date de patch dans la fenêtre adaptée.

### 8.3 La cascade « avec patchs »

`cascade_up_to_with_patches(date)` fait exactement la même chose que la version simple, **sauf** qu'à la date T :
- on regarde chaque `(asset, attack)` qui serait un seed,
- on vérifie si **toutes les attaques liées** ont été patchées avant T,
- si oui, on **retire ce seed** (l'actif est considéré comme protégé).

Résultat : la courbe **monte** quand de nouvelles attaques arrivent, **redescend** quand des patchs sont appliqués. Elle ressemble enfin à la vraie courbe de risque d'un SI.

---

<a id="9"></a>
## 9. Le dashboard — comment l'utiliser

Le notebook propose **trois dashboards interactifs** (à exécuter dans Jupyter pour que les widgets s'affichent) :

### 9.1 Dashboard §5 — par attaque
- **Choisis** une attaque dans la liste déroulante (les attaques sont triées par nombre de cibles).
- **Règle** la profondeur (jusqu'où la cascade se propage) et le seuil (en-dessous duquel on coupe).
- **Bascule** le mapper entre `hash` et `semantic` pour voir comment l'impact métier change.
- **Clique** sur ▶ Simuler.

Tu obtiens : KPIs, bar chart d'impact par processus, graphe de cascade.

### 9.2 Dashboard §6 — curseur temporel simple
- **Glisse** le curseur de date.
- On simule l'état du SI **à cette date**, en cumulant tous les événements antérieurs.

### 9.3 Dashboard §8d — combo final
Toutes les options des deux précédents, **plus** :
- Choix du mapper parmi les 4 (`hash`, `semantic`, `moa_synth`).
- **Case à cocher « patchs »** pour activer ou désactiver le modèle de recovery.

C'est celui-là qu'il faut utiliser pour des démos / livrables — c'est le plus complet.

---

## TL;DR — la chaîne de pensée du notebook

```
Données graphe (Neo4j)
     │
     ▼
Construction du graphe NetworkX (§1)
     │
     ▼
Simulation de cascade (BFS pondéré) (§2)
     │
     ▼ ─────────┬─────────────────────────────────────┐
     │         (a) impact technique : combien d'actifs ?
     │         (b) impact métier via ProcessMapper (§3, §8a)
     ▼
Dashboards interactifs (§5, §6, §8d)
     │
     ▼
Enrichissements optionnels :
   §8a · Carto synthétique réaliste
   §8b · Kill chain MITRE multi-phases
   §8c · Patchs et recovery
```

Tout est conçu pour qu'**un seul changement** (la vraie carto MOA, par exemple) **se branche en 10 lignes** sans casser le reste.
