# SISE Conso Analysis

Projet de Master 2 SISE : à partir des données DPE de l'ADEME ([logements existants](https://data.ademe.fr/datasets/dpe03existant) et [logements neufs](https://data.ademe.fr/datasets/dpe02neuf)), nous avons construit une application qui prédit l'**étiquette DPE** (A à G) et la **consommation d'énergie** (kWh/m²/an) d'un logement.

Trois départements sont couverts : Paris (75), Nord (59) et Rhône (69). Chacun a deux modèles : une classification (étiquette) et une régression (consommation).

## Accès en ligne

| Service | Adresse |
|---|---|
| Application | https://sise-conso-analysis-mguj.onrender.com |
| API (page de test) | https://sise-conso-analysis-api.onrender.com/docs |

Le plan gratuit de Render met les services en veille après environ 15 minutes sans visite : la première page peut mettre une minute à s'afficher.

## Fonctionnalités

- **Accueil** : présentation du projet et des pages.
- **Contexte** : données nettoyées, carte interactive et filtres. Les données peuvent être rafraîchies (mot de passe demandé).
- **Statistiques** : graphiques et indicateurs (KPI), exportables en .png.
- **Prédiction** : formulaire en étapes, étiquette DPE et consommation estimées, fiabilité du modèle affichée. Le modèle peut être ré-entraîné (mot de passe demandé).
- **API** : les mêmes modèles, accessibles sans l'interface.

## Installation

### 1. Récupérer le projet

```bash
git clone https://github.com/Abrlh/SISE-CONSO-ANALYSIS.git
cd SISE-CONSO-ANALYSIS
```

### 2. Variables d'environnement (facultatif)

Elles ne servent qu'au rafraîchissement des données et au ré-entraînement depuis l'application. Sans elles, l'application affiche « Apprentissage non configuré » et tout le reste fonctionne.

```bash
cp .env.example .env     # Windows PowerShell : copy .env.example .env
```

Remplir ensuite `GITHUB_DEPOT`, `GITHUB_TOKEN` et `MOT_DE_PASSE_ADMIN` dans `.env`. Ce fichier n'est jamais versionné (valeurs à demander à l’équipe).

### 3. Lancer avec Docker (recommandé)

Prérequis : Docker Desktop, lancé.

```bash
docker compose up --build
```

| Service | Adresse |
|---|---|
| Application | http://127.0.0.1:8501 |
| API (page de test) | http://127.0.0.1:8000/docs |

Pour arrêter : `docker compose down`.

### 4. Lancer avec Python

Prérequis : Python 3.13.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app/main.py          # application
```

Les données et les modèles sont déjà dans le dépôt. Pour refaire le pipeline complet :

```bash
python -m src.orchestration.train              # entraînement (télécharge les données si aucun snapshot)
python -m src.orchestration.train --refresh    # idem, avec un nouveau téléchargement
```

## API

| Route | Rôle |
|---|---|
| `GET /sante` | vérifie que l'API répond |
| `GET /departements` | départements disponibles |
| `GET /modeles/{tache}/{departement}` | variables attendues et métriques |
| `POST /predict` | prédit l'étiquette DPE et la consommation |

Le fichier [`docs/exemple_predict.json`](docs/exemple_predict.json) contient une requête complète, pour le département 59. Il y a deux façons de la tester, en local comme sur Render.

**Depuis la page `/docs`** (la plus simple) :
1. Ouvrir /docs : http://127.0.0.1:8000/docs en local, ou l’adresse Render.
2. Cliquer sur `POST /predict`, puis *Try it out*.
3. Coller le contenu de `docs/exemple_predict.json` dans la zone de texte, puis *Execute*.

**Depuis un terminal**, à la racine du projet :

```bash
curl -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" --data-binary "@docs/exemple_predict.json"
```

Sous PowerShell, utiliser `curl.exe`. Pour viser Render, remplacer l'adresse par celle de l'API en ligne.

La réponse donne l'étiquette et la consommation : `{"departement": "59", "etiquette_dpe": "D", "conso_kwh_m2_an": 170.5}`. Si une variable manque, l'API renvoie une erreur 422 qui la nomme.

## Tests

Depuis la racine du projet, après `pip install -r requirements.txt` :

```bash
python -m pytest
```

Les tests couvrent le nettoyage, les statistiques, le stockage, les modèles, l'API et le workflow de ré-entraînement.

## Structure du dépôt

| Dossier | Contenu |
|---|---|
| `app/` | application Streamlit |
| `src/` | code : données, nettoyage, modèles, pipeline, API |
| `data/` | données brutes, nettoyées et statistiques |
| `models/` | modèles entraînés et leur évaluation |
| `notebooks/` | exploration, nettoyage, machine learning |
| `tests/` | tests automatisés |
| `docs/` | documentation et schémas |
| `.github/workflows/` | workflows GitHub Actions (dont le ré-entraînement) |

## Documentation

- [Documentation fonctionnelle](docs/documentation_fonctionnelle.md)
- [Documentation technique](docs/documentation_technique.md)
- [Rapport d'étude](docs/rapport.md)
- [Architecture](docs/architecture_simple.md) et [diagramme de classes](docs/diagramme_classes.md)
- [Nettoyage des données](docs/nettoyage_donnees.md) et [analyse des données](docs/analyses_des_données.md)
- [Procédure de ré-entraînement](docs/procedure_reentrainement.md)
- [Déploiement (Docker et Render)](docs/deploiement.md)
