# Nettoyage des données DPE

Résumé de ce qui a été fait, de ce qui reste à faire et des points d'attention.
Le détail des décisions est dans `notebooks/02_nettoyage_donnees.ipynb`
(colonne par colonne dans `docs/colonnes_retenues.csv`, lignes supprimées dans `docs/bilan_nettoyage.csv`).

## Ce qui a été fait
- Le prétraitement est dans `src/preprocessing.py` (`DataPreprocessor.process`).
  L'interface est inchangée : `process({département: {nom_dataset: DataFrame}})` renvoie `{département: DataFrame}`.
- Il se lance avec : `python -m src.train --snapshot <id> --preprocess`
  (lit `data/raw/<id>/`, écrit `data/processed/<id>/`).
- Résultat sur le snapshot `2026-10-08_214716` : 58 644 lignes → 56 911 (1 733 supprimées, 3,0 %)
  et 224 colonnes → 31 par département (59 : 19 554 lignes, 69 : 19 349, 75 : 18 008).
- Les seuils et règles sont des constantes en haut de `preprocessing.py` : un seul endroit à modifier.

### Règles qui suppriment des lignes
Immeubles exclus (1 271), manquants sur surface / consommation / étiquette (324), surface hors de 9-500 m² (112),
consommation supérieure à 1 000 kWh/m²/an (14), émissions de GES supérieures à 1 000 kg CO₂/m²/an (12).

### Règles qui conservent la ligne
Coordonnées hors de la France métropolitaine → manquantes (202 lignes de Lille et Lyon, position erronée commune) ;
hauteur sous plafond hors de 1,8-5 m → manquante (125) ; énergies de chauffage rares regroupées ;
installation de chauffage / d'eau chaude manquante → « non applicable » (colonne vide pour les maisons).

## Conséquences pour le reste du projet
- Les fichiers de `data/processed/` ont désormais 31 colonnes (`_geopoint` est remplacée par `latitude` et `longitude`).
  Aucun code de `src/` ni de `app/` ne lisait ces fichiers au moment de la modification.
- Les colonnes `COLONNES_ANALYSE` (consommations par usage, coût, étiquette GES, émissions de GES, `ubat_w_par_m2_k`)
  sont gardées pour l'analyse et **ne doivent pas servir de variables d'entrée aux modèles** (elles contiennent déjà la réponse).

## Ce qui reste à faire

### Avant les modèles (dans le pipeline scikit-learn, pas dans le nettoyage)
- Imputer les manquants restants sur le jeu d'entraînement seulement : `qualite_isolation_plancher_bas` (2,7 %), `hauteur_sous_plafond` (0,2 %).
- Encoder : ordinal pour `periode_construction` et `qualite_isolation_*` (listes `ORDRE_PERIODE` et `ORDRE_ISOLATION`), `OneHotEncoder` pour les autres catégories.
- Choisir les variables d'entrée : à décider `hauteur_sous_plafond`, les qualités d'isolation (un particulier ne les connaît pas forcément), `origine` et le département.
- Étiquettes déséquilibrées (C domine, F et G rares) : découpage stratifié, pondération des classes, F1 macro et matrice de confusion.
- Évaluer aussi sur les logements existants seuls (les neufs sont presque tous en A, B ou C).
- Vérifier la sensibilité au seuil de consommation (refaire avec 800 au lieu de 1 000).

### Pour l'analyse et l'application
- Utiliser la **médiane** et la consommation **par m²** (`conso_5_usages_par_m2_ep`) pour les KPI et les graphiques.
- Ne pas additionner les consommations par usage : leur somme dépasse la consommation totale pour 51 % des lignes
  (cause non élucidée, à vérifier dans le dictionnaire de données de l'ADEME).
- Les 202 points sans coordonnées ne s'affichent pas sur la carte.
- Présenter les chiffres comme ceux de l'échantillon, pas du parc réel (voir limites).

## Mise à jour des données (nouveau snapshot)
Le nettoyage est du code : il se relance sur un nouveau snapshot sans intervention manuelle. À contrôler à chaque fois :
- **Le bilan** : une chute inhabituelle du nombre de lignes à une étape est un signal (le bilan n'est pas enregistré par `train.py`,
  il est dans `prepro.bilans` ; voir le notebook).
- **Les seuils** : ils viennent de l'échantillon actuel et peuvent ne plus convenir.
- **Les catégories** : une nouvelle période de construction ou un nouveau niveau d'isolation n'est pas géré (les énergies inconnues vont dans « Autre »).
- **Les doublons** entre anciens et nouveaux snapshots : `supprimer_doublons` ne travaille que sur un snapshot à la fois.
- **Les colonnes** : le code plante si une colonne clé est absente d'un département.
- À faire valider : comment `--refresh` télécharge-t-il (tout le jeu ou seulement les nouvelles lignes) ?

## Limites des données (à reprendre dans le rapport ML)
- Échantillon plafonné à 10 000 lignes par type et par département ; Paris compte 8 644 neufs (probablement tous).
- Pas un tirage aléatoire : existants de Lille et Lyon concentrés sur 2021 et 2026 (arrêt au 09/02/2026), ceux de Paris sur 2026.
  La proportion neufs / existants (environ 50/50) est un artefact de ce plafond. Pas d'étude de l'évolution dans le temps.
- Les neufs classés « immeuble » sont exclus, même ceux qui décrivent un logement isolé.
- Le sens des colonnes est déduit de leur nom : à confirmer dans le dictionnaire de données de l'ADEME.

## Questions ouvertes
- Le TODO de `train.py` (« DataPreprocessor.process à écrire ») est obsolète : à retirer par l'auteure du fichier.