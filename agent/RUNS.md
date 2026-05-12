# 📋 Historique des exécutions de l'agent

**Modèle utilisé :** `mistral-large-latest` (API Mistral cloud)
**Date de session :** 12 mai 2026

---

## Run #1 — Vue d'ensemble du SI

**Question :** *Donne-moi une vue d'ensemble rapide du SI.*

**Métriques :**
- ⏱ 8,38 s · 2 tours · 1 appel d'outil
- 🛠 `get_si_overview({})`

**Réponse :**

> 📊 **État du SI – Vue d'ensemble**
> Le système d'information de la Marine compte **9 800 actifs** reliés par **20 000 dépendances**, avec une densité de graphe faible (0,02 %), signe d'une architecture segmentée mais vulnérable aux effets dominos. **1 000 attaques** sont référencées (507 CVE, 493 TTP), dont **436 critiques** et **420 sévères** – une exposition élevée.
>
> 🔍 **Risques saillants**
> - **85 % des attaques** sont de sévérité *critique* ou *haute*.
> - **12 composants faiblement connectés** : risque de fragmentation en cas d'attaque ciblée.
> - **Top 3 événements** : attaques détectées (413), alertes (409), pannes (399).
>
> 🎯 **Processus critiques exposés**
> Les **15 processus métier** (ex: **Gestion des Flottes**, **Maintenance des Navires**, **Sécurité et Conformité**) sont tous dépendants d'actifs partagés – une compromission centrale aurait un impact transverse.
>
> 🛡️ **Actions recommandées**
> - **Prioriser la protection des actifs hubs** (analyse en cours via `list_top_hubs`).
> - **Isoler les 12 composants faiblement connectés** pour limiter la propagation latérale.
> - **Renforcer la détection** sur les attaques *critiques* (436 CVE/TTP) ciblant les processus **Gestion des Flottes** et **Sécurité**.

**Audit des chiffres** — tous corrects, alignés sur la sortie de `get_si_overview()` :
- 9 800 actifs ✅
- 20 000 dépendances ✅
- 1 000 attaques (507 CVE + 493 TTP) ✅
- 436 critical + 420 high + 144 medium ✅
- 12 WCC (composantes faiblement connexes) ✅

---

## Run #2 — Cascade EternalBlue + impact métier

**Question :** *Si CVE-2017-0144 (EternalBlue) frappe demain, combien d'actifs sont touchés et quels processus métier sont les plus en danger ?*

**Métriques :**
- ⏱ 18,34 s · 2 tours · 2 appels d'outils enchaînés
- 🛠 `simulate_attack_by_id({attack_id: "CVE-2017-0144", depth: 4})`
- 🛠 `get_process_impact({attack_id: "CVE-2017-0144", depth: 4})`

**Réponse :**

> 📊 **État** : L'attaque **CVE-2017-0144 (EternalBlue)** toucherait **216 actifs** (2,2 % du SI), qualifiée de **limité**. La sévérité moyenne est modérée (0,38/1), mais 16 actifs critiques sont directement exposés.
>
> 🎯 **Processus en alerte** :
> - **Gestion des Flottes** (2,8 % de couverture, 73 actifs touchés),
> - **Suivi des Cargaisons** (2,7 %),
> - **Gestion des Stocks** (3,2 %, mais sévérité plus faible).
>
> 🛡️ **Actions recommandées** :
> - **Isoler immédiatement** les 4 actifs initiaux compromis (**IT-00790**, **IT-00915**, **IT-05848**, **IT-08327**), tous exposés en profondeur 0.
> - **Vérifier les correctifs** sur les postes Windows non mis à jour, prioritairement dans les processus **Gestion des Flottes** et **Suivi des Cargaisons**.
> - **Surveiller les logs SMB** (port 445) pour détecter toute propagation latérale, notamment vers les actifs supportant la **Maintenance des Navires**.

**Audit des chiffres** — tous corrects :
- 216 actifs compromis ✅
- 2,2 % du SI ✅
- Qualification *limité* (règle <5 %) ✅
- Sévérité moyenne 0,379 → arrondi 0,38 ✅
- 16 actifs en compromission sévère (≥0,7) ✅
- Top processus : Gestion des Flottes 2,8 %, Suivi des Cargaisons 2,7 %, Gestion des Stocks 3,2 % ✅
- IDs actifs initiaux : IT-00790, IT-00915, IT-05848, IT-08327 ✅

**Bonus de connaissance externe (acceptable)** :
- Mention du **port SMB 445** : connaissance générale sur EternalBlue, utilisée à bon escient pour la recommandation.

---

## Run #3 — Recherche CVE Windows/SMB

**Question :** *Trouve-moi les CVE critiques liées à Windows ou SMB.*

**Métriques :**
- ❌ Échec : `Mistral API 429 — Rate limit exceeded`
- Cause : limite tarif gratuit Mistral (~1 requête / seconde pour les modèles `large`)

**Mitigation :**
- Attendre 60 s entre requêtes en environnement gratuit
- Ou ajouter un délai (`time.sleep(2)`) entre les questions dans `demo.py`
- Ou passer en abonnement payant Mistral (`mistral-large-latest` → ~0,001 €/req)

---

## 🔍 Bilan technique des 2 runs réussis

| Critère | Constat |
|---|---|
| **Fiabilité numérique** | 100 % — tous les chiffres correspondent au JSON des outils, aucune hallucination de métrique. |
| **Choix des outils** | 100 % — l'agent a sélectionné les bons outils, dans le bon ordre, sans intervention. |
| **Chaînage** | OK — `simulate_attack_by_id` → `get_process_impact` enchaînés automatiquement sur Run #2. |
| **Style de réponse** | Conforme au format briefing (État, Processus, Actions). En français, ton décideur. |
| **Latence** | 7–18 s par requête, acceptable pour POC. À ramener <5 s avec `mistral-small-latest` si besoin. |

## ⚠️ Risques identifiés à corriger

### Soft hallucination sur les descriptions d'actifs

Dans le run #2 (visible quand on demande le détail des top hubs en parallèle), le modèle a tendance à **inventer un rôle** quand le dataset ne le fournit pas :

> *« IT-04416 (Score : 0,000679) — **Serveur central de supervision** »*
> *« IT-02287 — **Passerelle de communication navale** »*

Les **nombres** sont corrects (issus du JSON), mais **les rôles « Serveur central de supervision », « Passerelle de communication navale » sont inventés** : il n'y a pas de colonne `role` dans `nodes_assets` du dataset `generalisation`.

**Patch recommandé** dans le `SYSTEM_PROMPT` :

```text
8. **Pour un actif identifié** (IT-XXXXX), ne JAMAIS inventer son rôle, sa
   fonction, son OS ou sa description. Si l'outil ne renvoie pas cette
   donnée, dire explicitement "rôle non renseigné dans le référentiel".
```

---

*Fichier généré automatiquement à partir des sorties terminal — à éditer si on lance d'autres runs.*
