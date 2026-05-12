# 📊 Strategic Pitch — Deliverable 1
**Sujet : Détection précoce de propagation IT → OT sur un système d'information naval**

---

## A. Define the Scope

**Problem Statement**
> Sur un bâtiment moderne de la Marine nationale, **les réseaux IT (bureautique, web) et OT (automates de propulsion, conduite de tir, navigation) ne sont plus isolés**. Une compromission d'un poste utilisateur ou d'un serveur web peut, via la chaîne de dépendances, atteindre un PLC. **Aujourd'hui, la détection est tabulaire et binaire** (alerte / pas d'alerte) ; elle **ignore la topologie** et ne mesure pas le « blast radius » d'une intrusion.

**Objective**
> Construire un **système de détection contextuelle d'attaques IT→OT** s'appuyant sur le **graphe d'actifs et de dépendances**, capable :
> 1. de **distinguer** les exploits qui restent confinés à l'IT de ceux qui menacent l'OT critique,
> 2. de **scorer chaque alerte par son rayon de souffle** (nombre d'actifs OT atteignables),
> 3. de **prioriser la réponse opérationnelle** sous contrainte de bande passante en mer.

---

## B. Establish the Relevancy

- **Doctrine officielle.** La Marine nationale identifie le **cyber comme 5ᵉ milieu de combat** (cf. Revue stratégique 2022, doctrine *Lutte Informatique Défensive* du ComCyber). Le risque IT/OT est **au cœur** des programmes *FREMM*, *FDI* et SNA *Suffren*, dont les automates pilotent des fonctions vitales.
- **Réalité du dataset.** Le jeu fourni reproduit fidèlement une architecture **Purdue** (workstation → serveur → HMI → PLC) avec un exploit Apache `CVE-2021-41773` injecté pendant 4 h. C'est **exactement** le scénario type d'un *initial access* sur un poste passerelle, pivotant vers l'OT.
- **Différenciation.** Plutôt qu'un n-ième détecteur d'intrusion (IDS/SIEM générique), notre approche **consomme le graphe Neo4j déjà natif** et s'aligne sur les outils que les SOC navals déploient (Cyberlibris, Sekoia, Harfang Lab + couche graphe interne).

---

## C. Argue the Importance — *So what?*

### Ce que ça change si on résout le problème

- **Réduction du MTTD (Mean Time To Detect)** sur la propagation IT→OT : objectif **< 60 s** vs plusieurs minutes aujourd'hui sur un SOC tabulaire.
- **Réduction du taux de faux positifs** en pondérant par criticité graphe : un exploit sur un poste **isolé** (zéro descendant OT) ≠ un exploit sur un serveur web qui contrôle 4 HMI.
- **Disponibilité opérationnelle du bâtiment** : éviter qu'un exploit web ne dégénère en arrêt propulsion ou en panne de conduite de tir en zone d'opération.

### Métriques en jeu

| Métrique | Référence sectorielle | Cible projet |
|---|---|---|
| **Recall** sur exploits OT-impactants | ~70 % (IDS classique) | **≥ 95 %** |
| **Précision** sur alertes critiques | ~30 % | **≥ 80 %** |
| **MTTD** propagation IT→OT | minutes | **< 60 s** |
| **Coût** d'une indispo OT en opération | indispo propulsion ≈ **immobilisation tactique** d'un bâtiment | non chiffré, **stratégique** |

### Pourquoi maintenant et pas dans 6 mois ?

- **Menace concrète et actuelle** : campagnes pro-russes (`Sandworm`) et iraniennes (`CyberAv3ngers`) ciblent activement des PLC depuis 2023–2025.
- **Fenêtre programme** : les retours d'expérience cyber des FREMM/FDI alimentent **dès maintenant** les spécifications du PA-NG (porte-avions de nouvelle génération) — toute brique de détection conçue ici peut **être versée au standard**.
- **Effet d'aubaine donnée** : le dataset de 50 000 événements + graphe étiqueté est **rare** ; bâtir le détecteur dessus aujourd'hui, c'est se donner une baseline reproductible pour tous les futurs exercices *DEFNET*.

---

### TL;DR (1 ligne)
> **Détecter, scorer et prioriser les attaques IT→OT à l'échelle d'un bâtiment, en exploitant nativement le graphe d'actifs — pour qu'un exploit web ne devienne jamais une avarie de propulsion.**
