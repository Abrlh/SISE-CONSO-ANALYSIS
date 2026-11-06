# Analyses statistiques pré-calculées

Ce document explique **comment et pourquoi** les statistiques de l'application sont calculées, ce que contient chaque tableau, et quels choix méthodologiques ont été faits. Il suffit à une personne qui découvre le projet pour comprendre, relire ou justifier les analyses.

Il complète `docs/nettoyage_donnees.md` (qui décrit la préparation des données) et s'arrête à la production des tableaux : l'affichage dans l'application n'est pas traité ici.

---

## 1. Principe : calculer une fois, lire ensuite

Le snapshot de référence contient environ 389 000 logements (3 départements, logements neufs et existants). Recalculer des médianes, des quartiles ou des corrélations sur cette taille à chaque clic d'un utilisateur serait lent et inutile.

On sépare donc deux temps :

1. **Calcul (une fois par snapshot)** : `python -m src.orchestration.train --snapshot <id> --stats` produit 20 petits tableaux, enregistrés sur disque.
2. **Lecture (à chaque affichage)** : l'application lit ces tableaux et sélectionne des lignes. Elle ne calcule rien.

Avantages :
- **Rapidité** : un tableau fait quelques kilo-octets (la table des logements, la plus grosse, 5,6 Mo).
- **Cohérence** : tous les utilisateurs voient les mêmes chiffres, issus du même calcul.
- **Testabilité** : le calcul est un code Python ordinaire, couvert par des tests unitaires.
- **Traçabilité** : chaque lot de tableaux est rattaché à un snapshot, avec sa date de calcul.

## 2. Chaîne de traitement

```
data/raw/<id>/            téléchargement brut (API ADEME)             --load
      │
      ▼
data/processed/<id>/      données nettoyées, un fichier par dépt      --preprocess
      │                     + meta.json (dont le bilan du nettoyage)
      │
      ▼
data/stats/<id>/          tableaux de statistiques + meta.json         --stats
      │
      ▼
AppService.get_stat(nom)  lecture par l'application
```

Commandes (à la racine du projet, environnement virtuel actif) :

| Commande | Effet |
|---|---|
| `python -m src.orchestration.train` | enchaîne téléchargement, nettoyage et statistiques |
| `python -m src.orchestration.train --snapshot <id> --stats` | recalcule seulement les statistiques d'un snapshot déjà nettoyé |
| `python -m src.orchestration.train --snapshot <id> --preprocess` | refait le nettoyage (les statistiques deviennent alors périmées : relancer `--stats`) |

Snapshot de référence utilisé pour ce document : `2026-10-12_132605` (départements 59, 69, 75 ; 393 952 lignes brutes, 388 717 après nettoyage).

## 3. Où sont les fichiers

- **Calcul** : `src/processing/analysis.py`, classe `StatAnalyzer` (méthode `compute_all`).
- **Stockage** : `src/data/repository.py` (`DataRepository`)
  - `save_stats(snapshot_id, tableaux)` : écrit un fichier `<nom>.parquet` par tableau, puis **en dernier** `meta.json`.
  - `list_stats(snapshot_id)`, `load_stat(snapshot_id, nom)`, `list_stats_snapshots()`.
  - `save_processed(..., nettoyage)` écrit le bilan du nettoyage dans le `meta.json` des données nettoyées ; `load_nettoyage(snapshot_id)` le relit (dictionnaire vide si le snapshot n'en a pas).
- **Lecture** : `src/orchestration/service.py` (`AppService.get_stat(nom)`), qui choisit automatiquement le snapshot le plus récent et garde les tableaux en mémoire.

Un snapshot dont `meta.json` est absent est considéré comme incomplet et ignoré : un calcul interrompu ne peut donc jamais être affiché.

`meta.json` des statistiques contient l'identifiant du snapshot, la liste des tableaux et la date de calcul (UTC).

**Bilan du nettoyage.** `DataPreprocessor.rapport()` met le bilan du nettoyage (lignes après chaque règle, colonnes retirées) sous forme de dictionnaire ; l'étape `--preprocess` l'enregistre dans `data/processed/<id>/meta.json`, clé `nettoyage`. L'étape `--stats` le relit pour produire les tableaux `bilan_nettoyage` et `colonnes_retirees`, sans refaire le nettoyage. Un snapshot nettoyé avant l'ajout de cette clé n'a pas de bilan : ces deux tableaux sont alors vides, et il suffit de relancer `--preprocess` puis `--stats`.

> `data/stats/` et `data/processed/` sont des fichiers générés : ils ne sont pas à versionner dans Git (voir le point ouvert en section 9).

## 4. Conventions communes à tous les tableaux

**Une analyse = une fonction.** Chaque fonction reçoit les données nettoyées (tous départements réunis) et renvoie un petit tableau. Les fonctions sont listées dans le dictionnaire `ANALYSES` en bas de `analysis.py` : ajouter une analyse, c'est écrire la fonction et l'ajouter à ce dictionnaire, le reste (calcul, enregistrement) est automatique. Exceptions : `qualite_donnees` et `apercu_donnees`, qui ont besoin des colonnes complètes de chaque département, et `bilan_nettoyage` et `colonnes_retirees`, qui partent du rapport du nettoyage et non des logements.

**Sous-totaux avec la valeur « Tous ».** Dans les colonnes `departement` et `origine`, la valeur `Tous` signifie « tous confondus ». Chaque tableau contient déjà toutes les combinaisons (par exemple département 75 + neufs, département « Tous » + existants, etc.). L'application n'a donc qu'à **choisir des lignes** ; aucun recalcul n'est nécessaire quand l'utilisateur change de filtre.

Techniquement, une fonction `_avec_total` duplique les lignes en remplaçant la valeur par « Tous » avant le groupement : un même `groupby` produit alors à la fois les détails et les sous-totaux.

**Colonne `origine`** : nom du jeu de données d'origine (logements existants ou neufs).

**Format « long ».** Les tableaux sont en format long (une ligne par combinaison), pratique pour tracer des graphiques par catégorie.

**Colonne manquante = tableau vide, pas d'erreur.** Si une colonne nécessaire à une analyse n'existe pas (par exemple après un rafraîchissement dont l'API a changé), l'analyse renvoie un tableau vide avec les bonnes colonnes. Le calcul complet ne s'arrête pas et l'application peut afficher « données non disponibles ».

**Valeurs manquantes.** Pour les variables qualitatives, une case vide devient la modalité `(non renseigné)` : on la voit au lieu de la perdre.

**Arrondis.** Pourcentages et médianes sont arrondis (1 ou 2 décimales) dès le calcul.

## 5. Colonnes ajoutées pour l'analyse

La fonction `_enrichir` crée trois colonnes à partir des données nettoyées (si la colonne source existe) :

| Colonne créée | Source | Règle |
|---|---|---|
| `famille_energie` | `type_energie_principale_chauffage` | Regroupe les nombreuses variantes en 6 familles : Électricité, Gaz naturel, Réseau de chaleur, Fioul, Bois, Autre. Les cases vides restent vides. |
| `tranche_surface` | `surface_habitable_logement` | 8 tranches : moins de 20 m², 20-30, 30-40, 40-60, 60-80, 80-100, 100-150, 150 m² et plus (borne basse incluse). |
| `annee_reception` | `date_reception_dpe` | Année de la date de réception du DPE. |

*Pourquoi regrouper l'énergie ?* Le champ brut contient beaucoup de libellés proches (plusieurs variantes d'électricité, de bois…). Les regrouper rend les graphiques lisibles et donne des effectifs suffisants.

## 6. Catalogue des tableaux

Dimensions mesurées sur le snapshot de référence (lignes × colonnes). « Périmètre » = chaque département + « Tous », croisé avec chaque origine + « Tous ».

### 6.1 Chiffres clés et étiquettes

| Tableau | Question | Colonnes | Taille |
|---|---|---|---|
| `kpi_globaux` | Combien de logements, quelle consommation, quelle part de passoires ? | `departement`, `origine`, `nb_logements`, `conso_mediane`, `surface_mediane`, `part_f_g`, `part_a_b` | 12 × 7 |
| `repartition_etiquettes` | Combien de logements par étiquette A à G ? | `departement`, `origine`, `etiquette`, `effectif`, `pourcentage` | 84 × 5 |

Les sept étiquettes sont toujours présentes (effectif 0 si nécessaire). Le pourcentage est calculé **à l'intérieur du périmètre** (il somme à 100 pour un département et une origine donnés).

### 6.2 Consommation

| Tableau | Question | Colonnes | Taille |
|---|---|---|---|
| `distribution_conso` | Comment la consommation se répartit-elle ? | `departement`, `origine`, `borne_min`, `borne_max`, `effectif`, `pourcentage` | 600 × 6 |
| `stats_conso` | Résumé statistique de la consommation | `departement`, `origine`, `effectif`, `moyenne`, `ecart_type`, `minimum`, `p05`, `q1`, `mediane`, `q3`, `p95`, `maximum` | 12 × 12 |
| `stats_numeriques` | Même résumé pour les autres variables numériques (surface, hauteur sous plafond, GES, coût) | `variable`, `departement`, `origine`, `effectif`, `nb_manquants`, `moyenne`, `ecart_type`, `minimum`, `p05`, `q1`, `mediane`, `q3`, `p95`, `maximum` | 60 × 14 |
| `conso_par_etiquette` | Quelle consommation par étiquette, selon l'énergie de chauffage ? (question du client) | `departement`, `origine`, `famille_energie`, `etiquette`, `effectif`, `moyenne`, `q1`, `mediane`, `q3` | 467 × 9 |

`stats_numeriques` couvre la consommation, la surface, la hauteur sous plafond, les émissions de GES et le coût ; `nb_manquants` compte les cases vides. La hauteur sous plafond vaut presque toujours 2,5 m (quartiles et médiane identiques), probablement une valeur par défaut du DPE : elle apporte peu d'information.

La consommation est `conso_5_usages_par_m2_ef` (kWh d'énergie finale par m² et par an, sur les 5 usages conventionnels du DPE : chauffage, eau chaude, refroidissement, éclairage et auxiliaires). C'est une consommation estimée selon des hypothèses standard, pas la facture réelle. L'étiquette DPE, elle, est calculée à partir de l'énergie primaire.L'histogramme utilise des tranches de 20 kWh/m²/an, de 0 à 1 000 (le plafond du nettoyage) ; toutes les tranches existent, même vides.
### 6.3 Facteurs explicatifs

| Tableau | Question | Colonnes | Taille |
|---|---|---|---|
| `conso_par_modalite` | Comment la consommation varie-t-elle selon chaque caractéristique ? | `variable`, `modalite`, `ordre`, `departement`, `origine`, `effectif`, `p05`, `q1`, `mediane`, `q3`, `p95`, `part_f_g` | 722 × 12 |
| `etiquette_par_modalite` | Quelle répartition des étiquettes dans chaque modalité ? | `variable`, `modalite`, `ordre`, `departement`, `origine`, `etiquette`, `effectif`, `pourcentage` | 5 054 × 8 |
| `correlations` | Quelles variables numériques varient ensemble ? | `origine`, `variable_x`, `variable_y`, `correlation` | 75 × 4 |

Variables qualitatives étudiées (celles qui n'existent pas dans les données sont ignorées) : période de construction, type de bâtiment, énergie de chauffage et sa famille, type d'installation de chauffage et d'eau chaude, qualité d'isolation (enveloppe, murs, menuiseries, plancher bas), tranche de surface.

La colonne `ordre` donne le rang d'affichage des modalités : ordre naturel pour les périodes et l'isolation, sinon de la plus fréquente à la moins fréquente.

Les corrélations portent sur : consommation, surface, hauteur sous plafond, émissions de GES, coût total.

### 6.4 Coût et émissions

| Tableau | Question | Colonnes | Taille |
|---|---|---|---|
| `cout_ges_par_etiquette` | Quel coût et quelles émissions par étiquette ? | `departement`, `origine`, `etiquette`, `effectif`, `conso_mediane`, `cout_par_m2_median`, `ges_median` | 75 × 7 |
| `etiquette_ges_vs_dpe` | L'étiquette GES suit-elle l'étiquette DPE ? | `origine`, `etiquette_dpe`, `etiquette_ges`, `effectif`, `pourcentage` | 147 × 5 |

Le coût par m² est `cout_total_5_usages / surface_habitable_logement`, **dans l'unité de la source**. Le croisement DPE × GES est une grille complète 7 × 7 ; le pourcentage est calculé par ligne (pour chaque étiquette DPE, répartition des étiquettes GES).

### 6.5 Temps

| Tableau | Question | Colonnes | Taille |
|---|---|---|---|
| `evolution_annuelle` | Que donne chaque année de réception ? | `departement`, `origine`, `annee`, `effectif`, `conso_mediane`, `part_f_g` | 72 × 6 |
| `couverture_temporelle` | Quelles dates couvrent les données ? | `departement`, `origine`, `nb_logements`, `date_min`, `date_max` | 12 × 5 |

⚠️ Ces deux tableaux sont à lire avec la réserve de la section 8.

### 6.6 Géographie

| Tableau | Question | Colonnes | Taille |
|---|---|---|---|
| `communes` | Quelles communes sont les plus ou les moins performantes ? | `departement`, `code_insee`, `commune`, `origine`, `effectif`, `conso_mediane`, `part_f_g`, `latitude`, `longitude` | 1 414 × 9 |
| `echantillon_points` | Où sont les logements ? (marqueurs de carte, nuage de points) | `departement`, `origine`, `etiquette_dpe`, consommation, surface, `latitude`, `longitude`, commune, période, type de bâtiment, famille d'énergie | 6 000 × 11 |

La position d'une commune est la **médiane** des coordonnées de ses logements. Les points hors de la France métropolitaine ont été retirés au nettoyage.

### 6.7 Données, qualité et nettoyage (page Contexte)

| Tableau | Question | Colonnes | Taille |
|---|---|---|---|
| `logements` | Table légère pour filtrer et exporter | 16 colonnes : département, origine, étiquette, consommation, surface, période, type de bâtiment, énergie et famille, tranche de surface, isolation de l'enveloppe, année, commune, code INSEE, latitude, longitude | 388 717 × 16 |
| `qualite_donnees` | Quelle part de cases vides par colonne ? | `departement`, `colonne`, `type`, `pct_manquant`, `presente` | 640 × 5 |
| `apercu_donnees` | Quelle est la taille des données nettoyées ? | `departement`, `nb_lignes`, `nb_colonnes`, `nb_numeriques`, `nb_dates`, `nb_texte` | 4 × 6 |
| `bilan_nettoyage` | Combien de lignes retire chaque règle du nettoyage ? | `departement`, `ordre`, `etape`, `lignes`, `lignes_retirees` | 52 × 5 |
| `colonnes_retirees` | Quelles colonnes ont été retirées car trop vides ? | `departement`, `colonne`, `pct_manquant` | variable |

La table `logements` est la seule à contenir une ligne par logement ; les textes y sont stockés en type `category` et les nombres en `float32` pour limiter la mémoire. `apercu_donnees` compte, pour « Tous », chaque colonne une seule fois même si elle existe dans plusieurs départements (d'où 160 colonnes pour « Tous » contre 159, 159 et 156 par département). Les colonnes sont réparties en numériques, dates et textes.

`bilan_nettoyage` a une ligne par règle appliquée (13 règles) et par département, plus « Tous » (somme des départements) ; `lignes` est le nombre de lignes après la règle, `lignes_retirees` celles qu'elle a supprimées. Sur le snapshot de référence : 393 952 lignes brutes, 4 130 immeubles exclus, 708 lignes sans valeur clé, 170 surfaces hors 5-500 m², 197 consommations supérieures à 1 000 et 30 émissions supérieures à 1 000, soit 388 717 lignes finales. Aucun doublon de numéro de DPE n'a été trouvé. `colonnes_retirees` donne le pourcentage de cases vides **avant** retrait, que `qualite_donnees` ne peut pas donner (une colonne retirée y apparaît à 100 %).

Pour `qualite_donnees`, une colonne retirée au nettoyage (trop vide) apparaît avec `presente = False` et compte pour 100 % de cases vides.

## 7. Choix méthodologiques et justifications

| Choix | Justification |
|---|---|
| **Médiane plutôt que moyenne** pour résumer la consommation, la surface, le coût | La consommation est asymétrique (quelques très gros consommateurs). La médiane n'est pas tirée par les valeurs extrêmes ; la moyenne est tout de même fournie dans `stats_conso` pour comparaison. |
| **Quartiles et percentiles 5 / 95** plutôt que toutes les valeurs | Ils suffisent à tracer une boîte à moustaches sans stocker 389 000 points. Les percentiles 5 et 95 donnent des moustaches qui ne sont pas écrasées par les valeurs aberrantes. |
| **Corrélation de Spearman** plutôt que Pearson | Elle mesure une relation croissante ou décroissante sans supposer une forme linéaire ni une distribution normale ; elle est peu sensible aux extrêmes. |
| **Passoire thermique = étiquette F ou G** | Définition réglementaire usuelle. Le taux `part_f_g` est utilisé partout avec cette définition. |
| **Histogramme par tranches de 20 kWh/m²/an** | Assez fin pour voir la forme de la distribution, assez large pour que chaque barre ait un effectif lisible. |
| **Communes de moins de 30 logements écartées** (`MIN_LOGEMENTS_COMMUNE`) | Sur très peu de logements, une médiane ou un pourcentage est trop instable pour être comparé. |
| **Échantillon de 2 000 points par département, graine fixe** (`POINTS_PAR_DEPARTEMENT`, `random_state=0`) | Afficher 389 000 marqueurs sur une carte la rendrait illisible et lente. Un échantillon aléatoire donne un aperçu représentatif ; la graine fixe garantit qu'il est identique à chaque calcul. |
| **Sous-totaux « Tous » pré-calculés** | Les médianes et quantiles ne s'additionnent pas : on ne peut pas retrouver la médiane de trois départements à partir de trois médianes. Il faut donc les calculer sur les données regroupées. |
| **Pourcentages calculés dans le périmètre** | Évite de comparer des pourcentages qui n'ont pas la même base. |
| **Tableaux en format long** | Un seul format pour tous les graphiques par catégorie, et facile à filtrer. |
| **Tout est calculé une seule fois sur les données nettoyées** | Les graphiques et les exports reposent exactement sur la même base que celle du modèle. |

## 8. Limites et précautions de lecture

1. **Échantillon non aléatoire dans le temps.** Le téléchargement interroge l'API par département seulement (`qs=code_departement_ban:<code>`), avec au plus 10 pages de 10 000 lignes par jeu de données, soit **100 000 lignes maximum par jeu et par département**, sans tri aléatoire. Résultat : pour les logements existants, la répartition par année est très inégale (par exemple 2021 : 68 438 ; 2022 : 198 508 ; 2023 : 5 682 ; 2024 : 1 097), et les existants s'arrêtent au 2026-02-09 alors que les neufs vont jusqu'au 2026-10-05. **`evolution_annuelle` ne montre donc pas une tendance réelle du parc.** Les étiquettes, consommations et autres analyses non temporelles ne sont pas affectées de façon connue, mais elles décrivent l'échantillon téléchargé, pas nécessairement tout le parc.
2. **« Tous » = les départements téléchargés** (actuellement 59, 69, 75), pas la France entière.
3. **Variables « de fuite ».** Les émissions de GES, le coût, les consommations par poste et les autres colonnes calculées par le DPE contiennent déjà la réponse. Elles sont utiles pour décrire et expliquer, mais **ne doivent pas servir d'entrées à un modèle de prédiction**.
4. **Corrélation n'est pas causalité.** Les tableaux montrent des associations (par exemple entre énergie de chauffage et étiquette), pas des effets.
5. **Unité du coût.** `cout_par_m2_median` est dans l'unité de la source (non convertie) : à utiliser pour comparer des étiquettes entre elles, pas comme un prix absolu.
6. **Immeubles exclus** par le nettoyage : les statistiques concernent les logements (maisons et appartements), pas les bâtiments entiers.
7. **Seuils du nettoyage** (surface 5-500 m², consommation ≤ 1 000, etc.) : ils influencent les distributions ; voir `docs/nettoyage_donnees.md`.

## 9. Tests et maintenance

- `tests/test_analysis.py` : une cinquantaine de tests sur un jeu de **8 logements dont les résultats ont été calculés à la main**. Le bilan du nettoyage est testé avec un rapport fictif de deux départements. Chaque tableau est vérifié (valeurs, sous-totaux « Tous », cas de colonnes manquantes, tableaux vides).
- `tests/test_service.py` : lecture des statistiques via un faux dépôt (choix du snapshot le plus récent, mise en cache, copie des tableaux, message d'erreur clair si rien n'est calculé).
- `tests/test_preprocessing.py` vérifie aussi que `rapport()` s'écrit en JSON et contient le bilan.
- Lancer : `python -m pytest tests -q`.

**Ajouter une analyse**
1. Écrire la fonction dans `src/processing/analysis.py` (entrée : un DataFrame ; sortie : un DataFrame ; tableau vide si une colonne manque).
2. L'ajouter à `ANALYSES`.
3. Ajouter un test sur le jeu de 8 logements.
4. Relancer `python -m src.orchestration.train --snapshot <id> --stats`.

**Après un rafraîchissement des données** : relancer `--preprocess` (qui enregistre aussi le bilan du nettoyage) puis `--stats` (ou la commande complète) ; l'application prend le snapshot le plus récent.

**Points ouverts à décider en équipe**
- Versionner ou non `data/stats/` (et retirer `data/processed/` du suivi Git).
- Corriger la limite de l'échantillon temporel (requêtes par plage de dates ou tri aléatoire) ; cela demande un nouveau téléchargement.
- Ajouter des tests statistiques (par exemple Kruskal-Wallis pour comparer la consommation entre groupes) si le rapport en a besoin.
