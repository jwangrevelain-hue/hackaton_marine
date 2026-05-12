# 🗺️ Deliverable 3 — Executive Presentation
## Détection précoce de propagation IT → OT sur SI naval

**Équipe :** Joseph W. · **Cible :** Marine Nationale (jury) · **Format :** 10 min + Q&A · **13 mai 2026**

> Ce fichier sert à la fois de **support de présentation** (chaque `---` = un slide) et de **script orateur** (notes de timing en italique). Convertible en PDF via le même pipeline que les livrables 1 et 2.

---

## Slide 1 — Title

# 🛡️ Détection précoce de propagation IT → OT
### Du graphe de dépendances au briefing décideur

**Joseph W. · Analyste Data · 13 mai 2026**
*Mission briefing à la Marine Nationale*

*[30 s — se présenter, poser le cadre : « 10 minutes pour vous prouver que le SOC d'un bâtiment ne voit pas la moitié du risque. »]*

---

## Slide 2 — The Hook · *« Ce que votre SOC ne voit pas »*

> **2 446 alertes anormales ne forment pas 2 446 incidents.**
> **Elles forment 1 propagation — et c'est ce que personne ne voit aujourd'hui.**

- Sur le bâtiment-école qu'on a étudié : **1 exploit Apache** (`CVE-2021-41773`)
- En 4 heures : **312 actifs compromis en cascade**, dont **20 systèmes OT** atteignables indirectement
- Aucun IDS ne signale cette **chaîne** — chacun regarde un actif à la fois

*[45 s — claquer le chiffre, fixer le problème. Pause de 2 s après « propagation ».]*

---

## Slide 3 — La Question · *« Mais alors, comment on décide ? »*

**Si une CVE sort demain, le commandant a 4 questions :**

1. **Qui** est touché ?
2. **Quels processus métier** sont en danger ?
3. **Combien** d'actifs faut-il isoler en priorité ?
4. **Quand** revient-on à la normale ?

**Notre projet répond aux quatre. En moins de 60 secondes par scénario.**

*[40 s — formuler les 4 questions clairement, regarder le jury. Transition : « Voici comment. »]*

---

## Slide 4 — Notre Méthode · *« Le graphe est la donnée »*

| Brique | Apport |
|---|---|
| **Cascade pondérée** sur le graphe de dépendances Purdue (10 k actifs, 20 k arêtes) | Mesure le *blast radius* réel d'une compromission |
| **4 mappers actif↔métier** (du placeholder à la vraie MOA) | Traduit le technique en impact métier — *agnostique au mapper* |
| **3 enrichissements composables** : carto synth MOA, kill chain MITRE, patchs | Modélise une attaque réaliste, pas un exploit isolé |
| **Briefing décideur** en français, KPI + actions top-5 | Sortie immédiatement actionnable pour le PC sécu |

**Stack technique 100 % open-source — souveraineté + reproductibilité audit.**

*[1 min — montrer qu'on a bâti sur des fondations solides. Pointer le notebook ouvert sur l'écran.]*

---

## Slide 5 — DÉMO LIVE · *« Le briefing en 30 secondes »*

> 🖥️ **Basculer sur le notebook** — section §10b « Dashboard décideur »

**Scénario joué devant le jury :**

1. Choisir la fenêtre temporelle (range slider) : « campagne du 15 mars au 28 août »
2. Patchs **activés** par défaut → vue réaliste
3. Cliquer ▶ Briefing

**Sortie attendue à l'écran :**
- 📊 État général : 🟧 *préoccupant* — 247 actifs compromis (2.5 % du SI)
- 🎯 Processus le plus exposé : *Maintenance des Navires* — 38 % de son périmètre
- 🚨 Processus en alerte rouge : *Maintenance, Gestion des Flottes, Sécurité*
- 🛡️ Top 5 actifs à isoler immédiatement
- 📋 Top 5 processus à protéger

*[2 min — démo réelle. Si bug, screenshots de secours dans le slide annexe. Ne PAS commenter le code, commenter le sens.]*

---

## Slide 6 — Insight #1 · *« 5 % des actifs portent 80 % du risque »*

**Loi de Pareto sur le PageRank :**

```
   Top 5 %  (≈ 500 actifs)  →  78 % du blast radius cumulé sur 50 simulations
   Top 20 % (≈ 2 000 actifs) →  94 % du blast radius cumulé
   80 %     (≈ 7 855 actifs) →  6 % du blast radius cumulé
```

> **Conséquence pour la Marine :** patcher au hasard, c'est gaspiller 80 % de l'effort.
> **Le ratio des bons hubs / des « long-tail » est de 1 : 16.**

**Recommandation immédiate :** identifier ces ~500 hubs sur chaque bâtiment et les inscrire au **plan de patching prioritaire** (RTO < 24 h sur ces seuls actifs).

*[1 min — c'est le 1er « non-obvious » du jury. Insister sur le 1:16. La donnée vient du notebook §1.1-1.2.]*

---

## Slide 7 — Insight #2 · *« Le résultat dépend du Mapper plus que de l'algorithme »*

**Même attaque (`CVE-2022-3238`, 295 actifs en cascade). 3 verdicts différents :**

| Mapper | Processus #1 selon le diagnostic | Lecture du décideur |
|---|---|---|
| `HashMapper` (neutre) | Communication Interne | Faux signal — artefact du hash |
| `SemanticMapper` (logs) | Sécurité et Conformité | Biais sémantique des descriptions |
| `SyntheticMOAMapper` | **Maintenance des Navires** | Plausible — cœur opérationnel |

> **La cartographie SI ↔ Métier est le levier #1 du projet.** Pas l'algorithme, pas la sévérité, pas la profondeur.

**Demande à la Marine :** investir 6 mois avec 3 ateliers MOA pour produire la **vraie** carto. Le reste de notre code l'absorbe en 10 lignes.

*[1 min 30 — point central pour le jury. Le pivot du pitch.]*

---

## Slide 8 — Insight #3 · *« Sans patchs, on pilote dans le brouillard »*

**Sur la même période, deux modèles donnent deux postures opposées :**

```
   Modèle SANS patch  →  courbe monotone croissante  →  « tout est cassé »
   Modèle AVEC patch  →  courbe montée-descente     →  posture réelle
```

L'**écart entre les deux courbes** = **valeur opérationnelle du SOC** = incidents évités par patching.

> **Quantification (estimation sur l'échantillon) :** sans modèle de patch dans le SIEM, le décideur surestime la dégradation du SI de **~60 % en moyenne** sur un horizon de 90 jours. C'est de la décision sur mauvaise donnée.

**Recommandation :** intégrer dans le SIEM un **état de patch par actif** (asset_id, CVE_id, patched_at). Donnée déjà disponible côté SCCM/WSUS — il suffit de la fusionner.

*[1 min — relier au business. La donnée vient du §10c du notebook.]*

---

## Slide 9 — Insight #4 · *« Pannes ≈ Attaques · l'investissement est dual-use »*

**Sur le rejeu temporel, les événements `Panne Système` génèrent des cascades comparables aux `Attaque Détectée` :**

- Mêmes hubs critiques touchés (recouvrement > 70 %)
- Mêmes processus métier dégradés (Maintenance, Flottes)
- Mêmes seuils de gravité

> **L'investissement cyber bénéficie à la résilience opérationnelle générale.** Un euro dépensé pour anticiper Sandworm protège aussi contre une avarie de climatisation salle serveur.

**Argument budgétaire :** le projet n'est pas un *cost center* sécurité — c'est un *investment* en disponibilité opérationnelle. Audit Cour des Comptes-compatible.

*[45 s — ouverture sur la justification budgétaire.]*

---

## Slide 10 — Recommandations · *« 3 actions, 3 horizons »*

### 🚀 90 jours · **POC SOC FREMM**
Brancher le moteur de cascade sur un flux SIEM réel d'une FREMM, en lecture seule. Calibrer le `threshold` et la `depth` sur des incidents historiques. **Livrable : rapport SOC + recommandation Go/No-Go pour passage à l'échelle.**

### 🎯 6 mois · **Cartographie MOA**
3 ateliers d'urbanisation (MOA + MOE + ComCyber) → CSV `asset_id, process_id, criticité`. Notre code l'absorbe sans modification d'architecture. **Livrable : `MOAMapper` opérationnel.**

### 🌊 18 mois · **Versement au standard PA-NG**
Apporter la brique « scoring graphe du blast radius » dans les spécifications cyber du Porte-Avions Nouvelle Génération, dès la phase de design. **Livrable : annexe technique au standard cyber DGA-MI.**

*[2 min — chaque reco a un horizon, un livrable, un porteur. C'est ce qu'on appelle de l'actionability.]*

---

## Slide 11 — Métriques cibles · *« Comment on saura qu'on a gagné »*

| Indicateur | Référence | Cible 90j (POC) | Cible 18m (standard) |
|---|---|---|---|
| **MTTD** propagation IT → OT | minutes | **< 60 s** | < 30 s |
| **Recall** sur exploits OT-impactants | ~70 % | ≥ 90 % | ≥ 95 % |
| **Précision** sur alertes critiques | ~30 % | ≥ 70 % | ≥ 80 % |
| **% de patchs prioritisés via PageRank** | 0 % | ≥ 50 % | 100 % |
| **% du parc avec mapping MOA validé** | 0 % | 20 % (POC FREMM) | 100 % FREMM/FDI |

*[45 s — chiffres mesurables, comparables à un état initial. Le jury peut tracer.]*

---

## Slide 12 — Ce qu'on attend de la Marine · *« L'ask »*

**Pour passer du POC à la production, trois choses :**

1. **Accès en lecture seule** aux logs SIEM d'une FREMM en exploitation (anonymisés) — 1 mois de données suffisent.
2. **3 demi-journées MOA** pour bootstraper la cartographie : commencer par 200 actifs critiques pilotes.
3. **Un parrain ComCyber** pour porter le sujet jusqu'à la décision standard PA-NG.

> **Coût total Marine sur 18 mois :** négligeable (3 demi-journées + accès SIEM). **Valeur :** un détecteur cyber natif graphe versé au standard.

*[40 s — l'ask est minimal et chiffré. C'est ce qui ferme la vente.]*

---

## Slide 13 — Synthèse · *« Pourquoi nous, pourquoi maintenant »*

> **Pourquoi nous ?** Notre code est *mapper-agnostic, time-aware, MITRE-native* — il accepte la vraie carto MOA en 10 lignes sans réarchitecturer.

> **Pourquoi maintenant ?** Sandworm et CyberAv3ngers ciblent activement les PLC depuis 2023. Les REX FREMM/FDI alimentent dès aujourd'hui les specs du PA-NG. **Toute brique versée maintenant entre au standard ; toute brique livrée dans 6 mois arrive trop tard.**

**Notre rôle :** vous donner un avantage *graphe-natif* que les SOC tabulaires concurrents n'auront pas.

*[40 s — closing fort. Regarder le jury, pause, transition Q&A.]*

---

## Slide 14 — Questions / Réponses

> 🎤 **Prêt à défendre sur :**

- **Méthodologie cascade** — pseudo-code BFS pondéré, seuils, complexité O(V+E)
- **Robustesse du mapper MOA-synth** — comparaison à `hash` et `semantic`, distribution-cible justifiée
- **Validité des patchs synthétiques** — windows 30-90j/critical alignées sur NIST CSF et CISA KEV
- **Souveraineté** — stack 100 % open-source, déployable air-gapped
- **Limites assumées** — pas de modèle stochastique, pas de threat intel campagne, mapper MOA synthétique à valider

---

## Annexes (en réserve si questions)

### A1 · Code source
- `EDA_GENERALISATION.ipynb` (51 cellules) — moteur, mappers, dashboards
- `EXPLICATIONS_GRAPHE.md` — méthode pas-à-pas pour non-experts
- `EXPLICATIONS_DONNEES.md` — dictionnaire de données

### A2 · Réponses pré-rédigées aux objections classiques

> *« Mais on a déjà un SIEM Splunk, vous arrivez après la bataille. »*
> → Notre brique se branche **en lecture** sur le SIEM. On ne remplace rien, on ajoute la dimension graphe que Splunk ne porte pas nativement.

> *« Les CVE de votre base ne sont pas validées CPE. »*
> → C'est explicitement listé dans nos gaps (Deliverable 2). On a la roadmap pour le résoudre via `nvdlib` en phase 3.

> *« Le mapper synthétique, c'est de la fiction. »*
> → Précisément — c'est un placeholder honnêtement annoncé, qui produit une couverture *structurellement* réaliste (cf. §8a-bis du notebook). Il sera remplacé en 10 lignes par la vraie carto MOA.

> *« 10 k actifs, c'est petit. À l'échelle FOST c'est 200 k. »*
> → NetworkX scale jusqu'à ~1 M nœuds en RAM. Au-delà, on passe sur Neo4j en backend graph DB — l'API du moteur ne change pas.

### A3 · Liens vers les autres livrables

- [Deliverable 1 — Strategic Pitch](PITCH_STRATEGIQUE.pdf)
- [Deliverable 2 — Intelligence Gathering](DELIVERABLE_2_INTEL.pdf)
- [Notebook complet](EDA_GENERALISATION.ipynb)

---

## Timing budgétaire (10 min)

| Section | Durée | Cumul |
|---|---|---|
| Slides 1-3 (intro, problème, question) | 1 min 55 | 1:55 |
| Slide 4 (méthode) | 1 min | 2:55 |
| Slide 5 (démo live) | 2 min | 4:55 |
| Slides 6-9 (4 insights) | 4 min 15 | 9:10 |
| Slide 10 (recos) | 2 min | *dépassement* — couper si nécessaire |
| Slides 11-13 (métriques + ask + closing) | 2 min 05 | — |

> ⚠️ **Si on déborde** : sacrifier l'insight #4 (slide 9, pannes ≈ attaques) — c'est le plus accessoire.

---

## Notes finales pour l'orateur

1. **Pas de jargon non-expliqué** : « blast radius » → toujours dit « rayon de souffle, c'est-à-dire le nombre d'actifs touchés ».
2. **Toujours relier au navire** : « Sur une FREMM, ça veut dire que… », « Sur un PA-NG en design… ».
3. **Le jury a la donnée** : ne pas leur expliquer ce qu'ils savent. Aller direct à *l'insight non-obvious*.
4. **Énergie** : pause de 2 secondes après chaque chiffre fort. Regarder un membre du jury différent à chaque slide.
5. **Q&A** : si on ne sait pas, dire « C'est dans nos gaps, voici comment on prévoit de le résoudre » — ne **jamais** bluffer.
