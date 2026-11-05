# Nettoyage des données DPE

Ce document explique, de bout en bout, ce qui est fait sur les données avant l'analyse et la modélisation : **quelles données utiliser, où les trouver, pourquoi elles sont faites ainsi, et comment les rafraîchir** quand un nouveau snapshot arrive.
Il est écrit pour que chacun, sans avoir suivi le travail de nettoyage, puisse comprendre les choix et les remettre en cause s'il le faut.

Pour le détail technique : le code est dans `src/preprocessing.py` (nettoyage) et `src/audit_colonnes.py` (contrôle des colonnes à chaque rafraîchissement).
Les décisions sont argumentées dans `notebooks/02_nettoyage_donnees.ipynb`, et les lignes retirées par règle sont dans `docs/bilan_nettoyage.csv`.

**Le principe en une phrase : le nettoyage corrige les erreurs et retire ce qui est inutilisable, mais il ne choisit pas les variables.** Toutes les colonnes de l'API sont conservées, sauf celles qui sont presque vides. Le choix des variables, le remplissage des valeurs manquantes, l'encodage et la découpe entraînement / test se feront à l'analyse et à la modélisation, avec l'ensemble de l'équipe.

---

## 1. Vue d'ensemble

Les données viennent de l'API de l'ADEME (DPE des logements existants et neufs). Elles passent par deux étapes, chacune écrite dans un dossier :

```
data/raw/<snapshot>/        données brutes de l'API, telles que reçues (un sous-dossier par département)
        │   nettoyage  (src/preprocessing.py)
        ▼
data/processed/<snapshot>/  données propres, toutes colonnes sauf les presque vides,
                            un fichier par département                                  ← ANALYSE et MODÈLES
```

Un **snapshot** est une photo des données à un moment donné (il porte la date de son téléchargement). Le snapshot de référence est **`2026-10-12_132605`** : trois départements (59, 69, 75), 393 952 lignes brutes, **388 717 logements après nettoyage** (5 235 retirés, soit 1,3 %).

| Département | Lignes brutes | Lignes propres | Colonnes |
|---|---|---|---|
| 75 (Paris) | 108 644 | 107 235 | 156 |
| 59 (Nord) | 140 344 | 138 807 | 159 |
| 69 (Rhône) | 144 964 | 142 675 | 159 |

Ce qu'il faut retenir :
- Les mêmes fichiers `data/processed` servent à l'**analyse** (graphiques, cartes, statistiques) et de **point de départ pour les modèles**.
- Ils contiennent **des cases vides** : elles ne sont pas remplacées (voir 4.4).
- Ils contiennent aussi des colonnes qui **donnent la réponse** (voir 3) : à ne pas utiliser en entrée d'un modèle.
- L'encodage et la découpe entraînement / test ne sont pas dans cette étape : ils seront décidés ensemble.

---

## 2. Où trouver les données et comment les obtenir

### Les ouvrir
Chemin : `data/processed/2026-10-12_132605/59.parquet`, `69.parquet`, `75.parquet` (un fichier par département).

```python
import pandas as pd
df = pd.read_parquet("data/processed/2026-10-12_132605/59.parquet")
```

Les valeurs sont lisibles (« Gaz naturel », « avant 1948 », « maison »), ce qui permet des graphiques, tableaux et filtres parlants dans Streamlit.
Pour avoir les trois départements ensemble : `pd.concat([...], ignore_index=True)`. Les départements n'ont pas exactement les mêmes colonnes (156 à 159) : au `concat`, une colonne absente d'un département est remplie de cases vides.

### Les obtenir : les données propres ne sont pas dans Git
Les fichiers de `data/processed` pèsent plus de 130 Mo en tout (de 38 à 51 Mo par département). Les mettre dans Git alourdirait le dépôt à chaque changement de règle, car Git garde toutes les versions. On **les régénère donc sur sa machine**, à partir des données brutes qui, elles, sont dans le dépôt :

Attention : des anciennes versions de ces fichiers sont encore suivies par Git (reste d’un ancien commit). Après un clone ou un pull, relancez toujours la commande ci-dessous, qui les écrase.
```
python -m src.train --snapshot 2026-10-12_132605 --preprocess
```

Après un `pull`, cette commande recrée `data/processed/2026-10-12_132605/`. Le résultat est identique pour tout le monde, puisque le code et les données brutes sont les mêmes.

### Plusieurs snapshots
Chaque snapshot a son propre dossier (`data/processed/<date>/`). Un nouveau snapshot n'efface pas l'ancien. Relancer le nettoyage sur le **même** snapshot réécrit seulement les fichiers de ce dossier. Pour être sûr du snapshot utilisé, toujours donner l'option `--snapshot <id>` ; sans elle, c'est le plus récent.

---

## 3. Les colonnes

### Toutes les colonnes sont gardées, sauf les presque vides
L'API fournit environ 220 colonnes par jeu (existants : 218 à 224 selon le département ; neufs : 182 à 196). Le nettoyage **ne sélectionne pas de variables** : pour ne pas décider à la place de l'équipe de ce qui servira, il garde tout, sauf les colonnes dont **plus de 80 % des valeurs sont manquantes** (constante `SEUIL_MANQUANT` en haut de `preprocessing.py`).
La règle s'applique **département par département**, sur les données déjà nettoyées. Les colonnes indispensables (numéro, étiquette, consommation, surface) ne sont jamais retirées.

Sur le snapshot de référence, 66 à 74 colonnes sont retirées selon le département. Ce sont des détails très peu renseignés : deuxième installation de chauffage, troisième énergie, panneaux solaires et production d'électricité, climatisation, copropriété, bâtiment tertiaire, etc. La liste exacte, avec le taux de manquants, est affichée par le contrôle du bilan (section 6, étape 4).

**Pourquoi 80 % ?** Beaucoup de colonnes ne concernent qu'une partie des logements (par exemple les maisons seulement) et sont naturellement vides pour les autres : un seuil bas retirerait des colonnes utiles. 80 % ne retire que les colonnes quasiment inutilisables. Le seuil est modifiable (une seule valeur) et à rediscuter avec l'équipe.

### Les nouvelles colonnes entrent automatiquement
Il n'y a plus de liste blanche : si l'API ajoute une colonne lors d'un rafraîchissement, elle est conservée (sauf si elle est trop vide). `src/audit_colonnes.py` permet de la repérer (section 6).

### Les colonnes qui donnent la réponse (à ne pas utiliser en entrée d'un modèle)
Les **cibles** sont `etiquette_dpe` (classification A à G) et `conso_5_usages_par_m2_ef` (régression, kWh/m²/an, énergie finale), définies dans `src/models/features.py`.
L'étiquette et la consommation sont **calculées à partir** d'autres colonnes du DPE : si on les donnait au modèle, il aurait d'excellents scores sans rien comprendre (c'est une **fuite de données**), et il serait inutilisable en vrai, puisqu'un utilisateur ne connaît pas ces valeurs avant d'avoir fait le diagnostic.
Les 9 colonnes les plus évidentes sont listées dans `COLONNES_ANALYSE` : `etiquette_ges`, `emission_ges_5_usages_par_m2`, `conso_5_usages_ep`, `conso_chauffage_ep`, `conso_ecs_ep`, `conso_eclairage_ep`, `conso_auxiliaires_ep`, `cout_total_5_usages`, `ubat_w_par_m2_k`.
Mais comme toutes les colonnes sont gardées, **il y en a d'autres** : en pratique, toute colonne dont le nom commence par `conso_`, `cout_`, `emission_ges`, `etiquette_`, `deperditions`, `besoin`, `ubat`, `apport_`, `production_` ou `indicateur_` est un résultat du calcul du DPE. L'audit (section 6) les signale. Elles sont utiles pour l'analyse (comprendre d'où vient la consommation, comparer les coûts), pas pour prédire.

### Les identifiants et la géographie
- `numero_dpe`, `date_reception_dpe` : identification. Peu d'intérêt pour prédire, et inconnus lors d'une prédiction.
- `code_departement_ban`, `code_postal_ban`, `nom_commune_ban`, `code_insee_ban` : géographie, utile pour les comparaisons entre territoires et les cartes par commune.
- `latitude`, `longitude` : créées à partir de `_geopoint` (« latitude,longitude » en un seul texte). Utiles pour les cartes de points. Pour les modèles, un utilisateur ne connaît pas ses coordonnées : **à décider par l'équipe modèles** (voir les questions ouvertes).

### Le sens des colonnes
Le sens des colonnes est déduit de leur nom : à confirmer dans le dictionnaire de données de l'ADEME.

---

## 4. Le nettoyage, règle par règle

Le code est dans `src/preprocessing.py`. Une fonction par règle, et tous les seuils sont des constantes en haut du fichier : pour changer un seuil, un seul endroit à modifier.
Le nettoyage s'applique **séparément à chaque département**, après fusion des logements existants et neufs (la colonne `origine` garde la trace de la provenance).
Il se lance avec `python -m src.train --snapshot <id> --preprocess` (lit `data/raw/<id>/`, écrit `data/processed/<id>/`).

### 4.1 Les règles qui retirent des lignes
Sur le snapshot `2026-10-12_132605`, dans l'ordre d'application :

| Règle | Critère | Pourquoi | Lignes retirées (59 / 69 / 75) |
|---|---|---|---|
| Doublons | un seul DPE par `numero_dpe` | un même diagnostic ne doit pas compter deux fois | 0 / 0 / 0 |
| Immeubles | on retire `type_batiment = immeuble` | un DPE d'immeuble décrit un bâtiment entier, pas un logement : il fausserait les moyennes par logement | 1 245 / 1 895 / 990 |
| Manquants clés | numéro, étiquette, consommation ou surface absents | sans eux, la ligne est inutilisable | 210 / 306 / 192 |
| Étiquettes | on garde A à G | toute autre valeur est une erreur | 0 / 0 / 0 |
| Surface | entre **5 et 500 m²** | en dessous, ce n'est pas un logement ; au-dessus, ce sont surtout des erreurs de saisie | 56 / 37 / 77 |
| Consommation | **supérieure à 0 et au plus 1 000 kWh/m²/an** | au-delà, valeurs extrêmes isolées, très probablement des erreurs ; le seuil est large pour ne retirer que l'aberrant | 26 / 21 / 150 |
| Émissions de GES | au plus **1 000 kg CO₂/m²/an** | des émissions impossibles (jusqu'à 5 900 observées à Lyon, avec une étiquette G fausse) | 0 / 30 / 0 |

**Les immeubles** ne sont pas des erreurs de données mais un choix sur la population étudiée : on s'intéresse aux logements. C'est un interrupteur : `TYPES_BATIMENT_EXCLUS = []` dans `preprocessing.py` les garde (dans ce cas, penser que le plafond de surface à 500 m² retirerait beaucoup d'immeubles). **À confirmer par l'équipe.**

**Pourquoi le seuil de surface est à 5 m² et non 9 m².** Le seuil de 9 m² (surface minimale d'un logement à la location) retirait à Paris 1 169 logements. On a regardé leurs surfaces : aucune à zéro, une seule entre 1 et 3 m², 53 entre 3 et 5, 288 entre 5 et 7 et 797 entre 7 et 9. Ce sont de vrais petits logements (chambres de bonne, petits studios), pas des erreurs. Les retirer aurait mal représenté Paris. Passer à 5 m² en récupère environ 1 050 et garde l'exclusion des valeurs absurdes.

Les autres seuils (500 m², 1 000 kWh/m²/an, 1 000 kg CO₂/m²/an) viennent d'un examen des valeurs extrêmes dans le notebook ; ce sont des seuils larges, qui ne retirent que de rares lignes (de 0 à 150 par département). Ils devraient être revérifiés à chaque grosse mise à jour (voir section 6), et la sensibilité au seuil de consommation (1 000 contre 800) reste à étudier.

**Ces règles ne portent que sur les colonnes connues** (surface, consommation, GES, hauteur). Les autres colonnes numériques, dont les nouvelles, n'ont pas de règle sur les valeurs extrêmes : pour des graphiques, préférer la médiane ou limiter l'axe.

### 4.2 Les règles qui gardent la ligne en corrigeant la valeur
On préfère corriger plutôt que supprimer quand la ligne reste utile.
- **Coordonnées hors de la France métropolitaine** (latitude hors de 41-52, longitude hors de -5,5-10) : remplacées par « manquant ». Dans les données de l'ADEME, une position erronée est commune à plusieurs logements de Lille et de Lyon. La ligne reste utile pour la consommation, mais ne s'affiche pas sur une carte. Pour une carte de points, écarter ces lignes : `df.dropna(subset=["latitude", "longitude"])`.
- **Hauteur sous plafond hors de 1,8-5 m** : remplacée par « manquant » (souvent une saisie en centimètres).
- **Espaces superflus** en début et fin de texte : supprimés, dans toutes les colonnes de texte (y compris celles qui apparaîtront plus tard).

Non vérifié : une coordonnée peut être dans la France mais pas dans le bon département. Ce contrôle n'est pas fait.

### 4.3 Les colonnes trop vides
Après les règles ci-dessus, on retire les colonnes vides à plus de 80 % (voir 3). Le bilan indique, pour chaque département, quelles colonnes sont retirées et leur taux de manquants.

### 4.4 Les valeurs manquantes sont conservées
Le nettoyage **ne remplace pas** les cases vides (ni par la médiane, ni par une valeur « inconnu »). Les raisons :
- remplacer, c'est inventer des valeurs ; la bonne méthode dépend de la colonne et du modèle ;
- si on calculait une médiane sur toutes les données, y compris la partie qui servira à tester le modèle, le modèle « verrait » un peu du test avant d'être évalué : ses scores seraient trop beaux. Ce remplissage doit se faire **à la modélisation, en apprenant sur l'entraînement seulement**.

Les cases vides sont de plusieurs natures, et il faut le savoir pour les interpréter :
- une colonne qui ne concerne pas ce type de logement (par exemple une installation collective pour une maison) ;
- une information absente de la saisie ;
- une valeur impossible que nous avons vidée (coordonnée, hauteur).

Les lignes sans numéro, étiquette, consommation ou surface sont en revanche retirées (4.1), car on ne peut rien en faire.

---

## 5. Utiliser les données : analyse et modélisation

### Pour l'analyse et la visualisation
Prendre `data/processed` tel quel : toutes les colonnes sont disponibles, y compris les résultats du calcul du DPE (consommation par usage, coût, émissions), utiles pour comprendre d'où vient la consommation. Penser aux cases vides (`dropna` sur les colonnes utilisées) et à la médiane plutôt qu'à la moyenne.

### Pour les modèles : ce qui reste à faire ensemble
Le nettoyage s'arrête volontairement avant la modélisation. Il restera à décider, en équipe :
1. **Le choix des variables** d'entrée, à partir de l'exploration. Exclure au minimum les colonnes qui donnent la réponse (section 3). Éviter aussi les identifiants.
2. **Le remplissage des valeurs manquantes**, appris sur l'entraînement seulement.
3. **L'encodage** des textes en nombres (les catégories ordonnées comme la période de construction ou la qualité d'isolation en rangs, les autres en colonnes 0/1).
4. **La découpe entraînement / test** : par département ou tous ensemble, stratifiée par étiquette, organisation des dossiers.
5. **L'évaluation** : les classes sont déséquilibrées (dans l'ordre de fréquence, C et D dominent, A et G sont rares) ; un modèle qui répondrait toujours « C » aurait déjà environ un tiers de bonnes réponses. Utiliser le **F1 macro**, la **matrice de confusion**, la pondération des classes, et évaluer aussi sur les logements existants seuls (les neufs sont presque tous en A, B ou C, la colonne `origine` permet de les séparer).

Une première proposition de découpe et d'encodage existe dans la branche `feature/preparation-modeles` ; elle sert de base de discussion, pas de décision.

---

## 6. Guide : rafraîchir les données avec un nouveau snapshot

À faire à chaque fois qu'un nouveau snapshot est disponible.

| Étape | Commande | Rôle |
|---|---|---|
| 1. Récupérer | `python -m src.refresh` | télécharge les données brutes dans `data/raw/<id>/` |
| 2. Auditer | `python -m src.train --snapshot <id> --audit` | colonnes utilisées par le code absentes ; colonnes apparues ou disparues depuis le snapshot précédent |
| 3. Nettoyer | `python -m src.train --snapshot <id> --preprocess` | écrit `data/processed/<id>/` |
| 4. Contrôler | (voir ci-dessous) | bilan des lignes et colonnes retirées |
| 5. Documenter | éditer ce document si une décision change | |

### Étape 1 : obtenir le snapshot
`python -m src.refresh` interroge l'API de l'ADEME et ne télécharge que si l'ADEME a publié une version plus récente que le dernier snapshot (le téléchargement se fait page par page). On peut aussi l'obtenir avec `python -m src.train --refresh`.
À confirmer : `train.py` appelle `refresh(size=10000)` en dur ; est-ce une taille de page ou un plafond du nombre de lignes ? Le plafond de 100 000 logements existants par département du snapshot actuel doit être documenté ici.
Attention : cette commande lance un vrai téléchargement (`--help` ne l'en empêche pas).

### Étape 2 : auditer les colonnes (à lancer avant de nettoyer)
`python -m src.train --audit` (ou `--snapshot <id> --audit`) contrôle les colonnes brutes du snapshot. Il **ne modifie rien** et n'a **aucun fichier de référence à tenir à jour**. Il affiche :
- **Colonnes utilisées par le code absentes** : doit afficher *toutes présentes*. Les listes sont lues dans le code : colonnes obligatoires du nettoyage, variables du formulaire des modèles (`src/models/features.py`), colonnes des statistiques (`src/analysis.py`). Pour chaque colonne absente, l'usage est indiqué. Une colonne obligatoire ou une variable du formulaire absente arrêtera de toute façon le nettoyage ou l'entraînement (`ColonnesManquantesError`) ; une colonne des statistiques absente donnera un tableau vide.
- **Par rapport au snapshot précédent** : les colonnes **disparues**, et les colonnes **nouvelles**, avec leur type, leur taux de manquants, des exemples de valeurs et une indication : « **ATTENTION** » (famille qui contient la réponse, à ne pas utiliser en entrée d'un modèle), « **Sera retirée par le nettoyage** » (vide à plus de 80 %), ou « **Entrera dans les données propres** ». Pour le premier snapshot, cette comparaison est sautée.

Un renommage par l'API apparaît comme une colonne disparue et une colonne nouvelle.
Les colonnes nouvelles sont aussi écrites dans `docs/audit_<snapshot>.csv`.
Le lancer à chaque **nouveau snapshot**, pas quand on relance le nettoyage sur le même snapshot.

### Étape 3 : nettoyer
`python -m src.train --snapshot <id> --preprocess`. Sans aucune option, `python -m src.train` enchaîne le chargement et le nettoyage.

### Étape 4 : contrôler le bilan
Afficher, pour chaque département, la taille du résultat, le nombre de lignes restantes après chaque règle, et les colonnes retirées :
```
python -c "from src.data.repository import DataRepository as R; from src.preprocessing import DataPreprocessor as P; r=R(); p=P(); out=p.process(r.load('<id>')); [print(d, out[d].shape, chr(10), p.bilans[d].to_string(), chr(10), p.colonnes_retirees[d].to_string()) for d in out]"
```
Ce qu'on cherche : le total retiré reste de l'ordre de 1 à 2 % ; aucune règle ne retire soudain beaucoup plus que d'habitude ; les colonnes retirées sont bien des colonnes quasi vides. Une règle qui s'emballe (par exemple la surface à Paris avec l'ancien seuil de 9 m²) est le signe qu'un seuil n'est plus adapté. C'est comme cela que ce seuil a été corrigé.
(`docs/bilan_nettoyage.csv` est écrit par le notebook ; `train.py` n'enregistre pas le bilan.)

### Étape 5 : documenter
Mettre à jour ce document si une décision a changé, puis enregistrer (commit). Les fichiers de `data/processed` ne se commitent pas.

### Ce qui est automatique et ce qui ne l'est pas
| Situation | Pris en charge ? |
|---|---|
| Règles de nettoyage sur les colonnes connues | oui, par l'étape `preprocess` |
| Colonne indispensable absente | oui : arrêt du nettoyage (`ColonnesManquantesError`) |
| Variable du formulaire absente | oui : arrêt de l'entraînement (`ColonnesManquantesError`, la même erreur) |
| Colonne des statistiques absente | tableau vide ; **signalé par l'audit (étape 2)** |
| Autre colonne disparue | les règles qui en dépendent sont ignorées ; **signalé par l'audit (étape 2)** |
| Nouvelle colonne de l'API | conservée automatiquement si elle n'est pas trop vide ; **repérée par l'audit (étape 2, lancée par `python -m src.train`)** |
| Valeur d'une catégorie renommée par l'API | **non détecté** : la valeur est traitée comme inconnue par les modèles |
| Colonne qui contient la réponse | **non filtrée** ; signalée par l'audit seulement |
| Seuils adaptés aux nouvelles données | **non** : à vérifier avec le bilan (étape 4) |
| Doublons entre ancien et nouveau snapshot | **non** : la déduplication ne travaille que sur un snapshot |
| Rafraîchissement lancé depuis l'application | télécharge un snapshot brut ; le **nettoyage et l'audit doivent être appelés ensuite** (`DataPreprocessor().process(...)`) : à brancher dans `AppService` |

---

## 7. Limites des données (à reprendre dans le rapport)
- **Échantillon plafonné** : 100 000 logements existants par département (plafond atteint dans les trois). Les logements neufs (8 644 à Paris, 40 344 dans le Nord, 44 964 dans le Rhône) sont sous le plafond, donc probablement complets. Le poids des neufs varie beaucoup : environ 8 % à Paris contre 29 à 31 % ailleurs.
- **Pas forcément un tirage aléatoire.** Sur l'ancien snapshot de 10 000 lignes, les existants de Lille et Lyon étaient concentrés sur 2021 et 2026, ceux de Paris sur 2026. À revérifier sur le snapshot de 100 000 lignes avant toute conclusion sur l'évolution dans le temps.
- **Trois départements seulement** : les modèles ne sont fiables que pour des logements comparables.
- **Immeubles exclus**, même les neufs qui décrivent un logement isolé.
- **Cases vides conservées** : les colonnes gardées contiennent jusqu'à 80 % de cases vides. Une analyse ou un modèle doit les gérer explicitement.
- Environ 1 % des logements sont retirés parce qu'ils manquent d'une information essentielle ou ont une valeur aberrante, alors que d'autres informations seraient valables.
- Ne pas additionner les consommations par usage : sur l'ancien snapshot, leur somme dépassait la consommation totale pour 51 % des lignes (cause non élucidée, à vérifier dans le dictionnaire de l'ADEME).
- Pour les KPI et les graphiques, préférer la **médiane** (robuste aux valeurs extrêmes) et la consommation **par m²**. Présenter les chiffres comme ceux de l'échantillon, pas du parc réel.

---

## 8. Questions ouvertes
- **Immeubles** : exclus par défaut ; à confirmer par l'équipe.
- **Seuil de colonnes vides** (80 %) et **seuil de consommation** (1 000 contre 800 kWh/m²/an) : sensibilité à étudier.
- **Données propres** : régénérées à la demande plutôt que stockées dans Git ; à confirmer par l'équipe.
- **Définition des KPI**.
- **Localisation dans les modèles** (latitude / longitude, département) : comparer avec et sans.
- **Découpe entraînement / test** : par département ou non, organisation des dossiers.
- **Snapshot de 100 000 lignes** : comment il est produit, sens de `size=10000` dans `refresh`, échantillon aléatoire

---

## 9. Mini-glossaire
- **Snapshot** : photo des données de l'API à un moment donné, stockée dans un dossier daté.
- **Parquet** : format de fichier de tableau, compact et rapide (on s'en sert à la place du CSV).
- **Imputer** : remplacer une valeur manquante (par la médiane, par exemple).
- **Encodage** : transformer du texte (« Gaz naturel ») en nombres que le modèle comprend.
- **Fuite de données** : donner au modèle, sans le vouloir, la réponse ou une information du jeu de test. Résultat : des scores trop beaux et un modèle inutilisable en vrai.
- **Médiane** : valeur du milieu quand on trie les données ; moins sensible aux valeurs extrêmes que la moyenne.
