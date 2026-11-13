# Documentation technique

L'application est composée d'une **interface Streamlit** et d'une **API FastAPI**, conteneurisées avec Docker et déployées sur Render.

Dépôt Github : [SISE-CONSO-ANALYSIS](https://github.com/Abrlh/SISE-CONSO-ANALYSIS).

## 1. Architecture

<img src="https://codimd.math.cnrs.fr/uploads/upload_214a06c9d15bd366502455c47cbd0a69.png" width="100%">

*Figure 1 : architecture de l'application*

- **Interfaces** : l'application Streamlit (`app/`) et l'API FastAPI (`src/api/`) passent toutes les deux par `AppService`, **le seul point d'entrée** vers les données, les statistiques et les modèles (détail des classes en figure 2).
- **Fichiers** : `data/raw`, `data/processed`, `data/stats` et `models/` sont rangés **par snapshot**.

<img src="https://codimd.math.cnrs.fr/uploads/upload_7aab7bf51a47ac6a020462b74e13c050.png" width="100%">

*Figure 2 : diagramme de classes*

## 2. Packages nécessaires

Avec Python **3.13**, les packages installés dans l'image sont les suivants (`requirements-docker.txt`) :

| Package | Version | Rôle |
|---|---|---|
| `streamlit` | 1.65.0 | interface web |
| `pandas` | 3.0.6 | manipulation des données |
| `numpy` | 2.5.3 | calcul numérique |
| `scikit-learn` | 1.9.1 | modèles |
| `scipy` | 1.18.1 | calcul scientifique |
| `joblib` | 1.6.0 | sauvegarde des modèles |
| `pyarrow` | 25.0.1 | fichiers .parquet |
| `requests` | 2.34.2 | appels à l'API de l'ADEME |
| `PyYAML` | 6.0.3 | configuration |
| `plotly` | 7.1.0 | graphiques et cartes |
| `fastapi` | 0.162.4 | API |
| `uvicorn` | 0.54.0 | serveur de l'API |

## 3. Installer l'application avec Docker

**Prérequis** : Il faut lancé **Docker Desktop**, et installé **Git**.

1. **Récupérer le code** : `git clone https://github.com/Abrlh/SISE-CONSO-ANALYSIS.git`, puis `cd SISE-CONSO-ANALYSIS`.
2. **Lancer** : `docker compose up --build`
3. **Ouvrir** dans le navigateur :

   | Service | Adresse |
   |---|---|
   | Application Streamlit | http://127.0.0.1:8501 |
   | API (page de test) | http://127.0.0.1:8000/docs |

4. **Arrêter** : `Ctrl+C`, puis `docker compose down`.

Une seule image contient le code, les données préparées et les modèles, **allégés à la construction** pour tenir dans les 512 Mo de RAM de Render.

Le rafraîchissement des données et le ré-entraînement **ne s'exécutent pas dans le conteneur** : les boutons de l'application lancent un workflow **GitHub Actions** sur le dépôt, ce qui demande un fichier `.env` (modèle : `.env.example`, **jamais versionné**). Une fois le workflow terminé, il faut récupérer le résultat (`git pull`) puis relancer `docker compose up --build`. Sans ce fichier, tout le reste de l'application fonctionne normalement.

## 4. Déploiement sur Render

L'application Streamlit et l'API sont hébergées sur Render, en deux services Docker construits depuis la même image.

| Service | Adresse |
|---|---|
| Application Streamlit | https://sise-conso-analysis-mguj.onrender.com |
| API (page de test) | https://sise-conso-analysis-api.onrender.com |

Les modèles étant dans l'image, chaque ré-entraînement demande un **redéploiement** sur Render. Le plan gratuit met les services en veille : le premier chargement peut prendre environ une minute. La procédure est détaillée sur le dépôt GitHub : `docs/deploiement.md`.