# Diagramme de classes - SISE-CONSO-ANALYSIS

Application Streamlit dockerisée d'analyse des DPE (API ADEME) : récupération des données, prétraitement, modèles de classification et de régression, statistiques descriptives.

![Diagramme de classes](dc.drawio.svg)

Le diagramme liste les attributs et les méthodes publiques de chaque classe. Les fichiers sans classe (fonctions seules) sont représentés avec le stéréotype «module».

## Rôle des classes

| Couche        | Classe ou module                          | Rôle                                                                                                                                              |
| ------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Config        | `Settings`                                | Lit `config/tasks.yaml`. Non utilisée : aucun module ne l'importe et le fichier est absent du dépôt                                               |
| Stockage      | `Storage` / `LocalStorage`                | Lecture et écriture des fichiers parquet sur disque. `alleger` réduit un fichier aux colonnes demandées                                           |
| Données       | `AdemeApiClient`                          | Appels HTTP à l'API ADEME (DPE existants et neufs), sans logique métier                                                                           |
| Données       | `DataRepository`                          | Snapshots datés des données brutes, prétraitées et des statistiques. Tient `data/snapshot_actif.json` (snapshot et version de modèles affichés)   |
| Traitement    | `DataPreprocessor` + `preprocessing`      | Fusion existants / neufs par département, puis nettoyage (fonctions d'étape du module)                                                            |
| Traitement    | `StatAnalyzer` + `analysis`               | Calcule tous les tableaux de statistiques (fonctions du module). Renvoie des DataFrames, jamais de graphiques                                     |
| Traitement    | `audit_colonnes`                          | Compare les colonnes d'un snapshot aux colonnes utilisées par le code et à celles du snapshot précédent                                           |
| Traitement    | `ColonnesManquantesError`                 | Levée quand une colonne attendue par le code est absente des données                                                                              |
| Modèles       | `BaseModel`                               | Interface commune : `train`, `predict`, `evaluate`, `tableaux_evaluation`, `importance_variables`                                                 |
| Modèles       | `ClassificationModel` / `RegressionModel` | Étiquette DPE et consommation. Pipeline scikit-learn et métriques propres à chaque tâche                                                          |
| Modèles       | `features`                                | Cibles des deux tâches et variables du formulaire. `preparer_xy` sépare X et y                                                                    |
| Modèles       | `ModelRegistry`                           | Enregistre et recharge les modèles, leurs métadonnées et leurs tableaux de performance, par version, tâche et département                         |
| Orchestration | `TrainingPipeline`                        | Étapes `load`, `audit`, `preprocess`, `stats`, `train`. Publie la nouvelle version puis supprime les anciens snapshots                            |
| Orchestration | `AllegementImage`                         | Garde le snapshot et la version publiés, réduit `data/processed` aux colonnes des modèles (image Docker, workflow GitHub)                         |
| Orchestration | `WorkflowGitHub`                          | Lance et suit le workflow de réentraînement (`.github/workflows/retrain.yml`) via l'API GitHub                                                    |
| Orchestration | `refresh`                                 | Script : télécharge un nouveau snapshot (`DataRepository.refresh`)                                                                                |
| Orchestration | `AppService`                              | Façade : point d'entrée du front vers les statistiques pré-calculées, les modèles et le formulaire                                                |
| Front         | `main` + pages                            | `main` déclare les quatre pages (accueil, contexte, statistiques, prédiction). Affichage et widgets uniquement                                    |
| Front         | `deps`, `tableaux`                        | `get_service` crée l'unique `AppService`. `lire` rend un tableau de statistiques mis en cache                                                     |
| Front         | `reentrainement`                          | Bloc de la page Prédiction : formulaire protégé par mot de passe et suivi du workflow                                                             |
| Front         | `affichage`, `graphiques`, `style`        | Libellés et filtres partagés, graphiques Plotly, habillage CSS                                                                                    |

## Principes retenus

1. **Séparation back / front** : `src/` n'importe jamais Streamlit. Le back renvoie des `DataFrame`, `dict` ou `ndarray`. Les graphiques sont produits dans `app/`.
2. **Façade** : les pages passent par `AppService`, instancié une seule fois avec `@st.cache_resource` (`app/deps.py`). Seule exception : `app/reentrainement.py` utilise directement `WorkflowGitHub`.
3. **Entraînement hors de l'application** : `TrainingPipeline` est lancé en ligne de commande, ou par le workflow GitHub Actions déclenché depuis la page Prédiction. L'application ne fait que charger les modèles (lecture seule).
4. **Statistiques pré-calculées** : l'étape `stats` du pipeline écrit les tableaux dans `data/stats/<snapshot_id>/`. L'application les lit, elle ne calcule rien.
5. **Snapshots datés** : `DataRepository.refresh()` télécharge les données de chaque département dans `data/raw/<snapshot_id>/`. `meta.json` est écrit en dernier : un snapshot sans ce fichier est ignoré.
6. **Publication** : `data/snapshot_actif.json` désigne le snapshot de données et la version de modèles affichés. Il est mis à jour à la fin de l'entraînement et lu par `AppService` au démarrage.
7. **Cibles dans le code** : cibles et variables du formulaire sont définies dans `src/models/features.py`.
8. **Héritage limité** : `BaseModel` (polymorphisme sur `train`, `evaluate`, `tableaux_evaluation`) et `Storage`.

## Flux

```
[1] Rafraîchir   python -m src.orchestration.refresh   API ADEME -> data/raw/<snapshot_id>/   (facultatif, voir [2])
[2] Entraîner    python -m src.orchestration.train     snapshot -> audit -> prétraitement -> statistiques -> models/<version>/
                 Réutilise le dernier snapshot, télécharge seulement s'il n'y en a aucun.
                 --refresh : télécharge un nouveau snapshot   --snapshot <id> : utilise ce snapshot
                 --load --audit --preprocess --stats --train : étapes à lancer (par défaut : toutes)
[3] Alléger      python -m src.orchestration.alleger   simulation ; --ecrire avec ALLEGER_ECRITURE=1 (image Docker, workflow GitHub)
[4] Servir       streamlit run app/main.py   snapshot et modèles publiés, lecture seule
```

Contenu d'une version de modèles :

```
models/<version>/<tache>/<departement>/
  model.joblib             # objet modèle complet (pipeline scikit-learn compris)
  evaluation/<nom>.parquet # tableaux de performance pour le front
  meta.json                # snapshot source, cible, colonnes, métriques ; écrit en dernier
data/snapshot_actif.json   # snapshot de données et version de modèles affichés
```

## Arborescence

```
src/                                 # un dossier par couche du diagramme
  config/settings.py                 # Configuration : Settings (non utilisée)
  storage/storage.py                 # Stockage : Storage, LocalStorage
  data/api_client.py                 # Données : AdemeApiClient
  data/repository.py                 # Données : DataRepository
  processing/preprocessing.py        # Traitement : DataPreprocessor, ColonnesManquantesError, fonctions de nettoyage
  processing/analysis.py             # Traitement : StatAnalyzer, fonctions d'analyse
  processing/audit_colonnes.py       # Traitement : audit des colonnes
  models/base.py                     # Modèles : BaseModel
  models/classification.py           # Modèles : ClassificationModel
  models/regression.py               # Modèles : RegressionModel
  models/features.py                 # cibles et variables du formulaire
  models/registry.py                 # Modèles : ModelRegistry
  orchestration/refresh.py           # point d'entrée [1]
  orchestration/train.py             # TrainingPipeline, point d'entrée [2]
  orchestration/alleger.py           # AllegementImage, point d'entrée [3]
  orchestration/workflow_github.py   # WorkflowGitHub
  orchestration/service.py           # AppService
app/
  main.py                # point d'entrée [4] : configuration et menu
  pages/accueil.py
  pages/contexte.py
  pages/statistiques.py
  pages/prediction.py
  deps.py                # get_service
  tableaux.py            # lecture des statistiques
  reentrainement.py      # bloc de réentraînement
  affichage.py           # libellés et filtres partagés
  graphiques.py          # graphiques Plotly
  style.py               # habillage CSS
  lecture.py             # lecture directe de data/processed, non importée par les pages
Dockerfile               # copie le dépôt, allège data/ et models/, lance streamlit
```
