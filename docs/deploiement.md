# Déploiement : Docker, Render et API

Ce document explique comment l'application Streamlit et l'API des modèles sont conteneurisées
(Docker), lancées en local (`docker compose`) et déployées sur internet (Render), et comment les
mettre à jour après un réentraînement.

## 1. Vue d'ensemble

```
                    GitHub (branche master)
          code + data/processed + data/stats + models/
              |                         ^
              | build Docker            | commit des nouveaux
              v                         | modèles et données
   +----------------------+      +---------------------------+
   |   Render             |      |   GitHub Actions          |
   |  - service "app"     |      |   workflow retrain.yml    |
   |  - service "api"     |      |   (rafraîchit, réentraîne)|
   +----------------------+      +---------------------------+
          ^                                   ^
          | HTTP                              | déclenché depuis la page
   utilisateurs / autres                      | « Apprentissage » (jeton + mot de passe)
   programmes (API)
```

- **Une seule image Docker** contient le code, les données préparées et les modèles. Elle sert à la fois
  l'application (Streamlit, port 8501) et l'API (FastAPI) : seule la commande de démarrage change.
- **Le réentraînement n'a pas lieu dans le conteneur** : il s'exécute sur GitHub Actions
  (`retrain.yml`) et committe les nouveaux modèles sur `master`. Il faut ensuite **reconstruire l'image**
  (redéploiement) pour que l'application et l'API servent les nouveaux modèles.
- **L'application et l'API passent par la même classe** (`AppService`) : elles donnent les mêmes
  prédictions.

## 2. L'image Docker

Fichiers : `Dockerfile`, `.dockerignore`, `requirements-docker.txt`, `docker-compose.yml`.

| Élément | Choix | Raison |
|---|---|---|
| Base | `python:3.13-slim` | image légère |
| Dépendances | `requirements-docker.txt` (liste minimale) | `requirements.txt` est un export complet (tests, notebooks...) inutile dans l'image |
| Fichiers exclus | `.dockerignore` | les données brutes volumineuses n'entrent pas dans l'image |
| Allègement | `RUN ALLEGER_ECRITURE=1 python -m src.orchestration.alleger --ecrire` | ne garde, dans les données préparées, que les colonnes utiles aux modèles |
| Démarrage | `streamlit run ...` sur le port de la variable `PORT` (8501 par défaut) | Render fournit son propre port |

**Pourquoi alléger.** Le plan gratuit de Render limite la mémoire vive à 512 Mo. Le formulaire de prédiction
charge les données préparées de chaque version de modèle. Sans allègement, la mémoire dépassait la
limite. Avec seulement les colonnes des modèles, l'application consomme environ 340 Mo (mesuré avec
`docker stats`). L'allègement est fait par la classe `AllegementImage` (`src/orchestration/alleger.py`),
qui s'appuie sur `LocalStorage.alleger` et `DataRepository.alleger_processed`. Il ne conserve que les
deux derniers snapshots publiés. Le message « JSONArgsRecommended » affiché à la construction est un
simple avertissement de style, sans conséquence.

## 3. Lancer en local avec Docker

Prérequis : Docker Desktop installé **et lancé**.

```bash
docker compose up --build
```

| Service | Adresse | Rôle |
|---|---|---|
| `app` | http://127.0.0.1:8501 | application Streamlit |
| `api` | http://127.0.0.1:8000/docs | API des modèles |

`127.0.0.1` désigne l'ordinateur de la personne qui lance Docker : ces adresses sont identiques sur
tous les postes mais ne fonctionnent que sur la machine qui exécute les conteneurs, et seulement tant
que `docker compose up` tourne. Les ports sont fixés dans `docker-compose.yml`.

Commandes utiles :

```bash
docker compose down              # arrêter et nettoyer
docker compose logs -f api       # suivre les journaux d'un service
docker stats                     # consommation mémoire des conteneurs
docker run --rm -p 8000:8000 sise-conso python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
                                 # lancer l'API seule, sans compose
```

## 4. Variables d'environnement et secrets

Le rafraîchissement des données et le réentraînement exigent trois variables. L'application les lit au
démarrage ; si elles manquent, elle affiche « Apprentissage non configuré » et le reste fonctionne.

| Variable | Rôle |
|---|---|
| `GITHUB_DEPOT` | dépôt GitHub dont on lance le workflow de réentraînement |
| `GITHUB_TOKEN` | jeton GitHub (voir ci-dessous) |
| `MOT_DE_PASSE_ADMIN` | mot de passe demandé dans la page « Apprentissage » |
| `GITHUB_BRANCHE` | facultative, `master` par défaut |

**En local :** copier `.env.example` en `.env`, remplir les valeurs, puis relancer `docker compose up`.
Les variables sont fournies au démarrage du conteneur : **jamais dans l'image** ni dans le `Dockerfile`.

**Règles de sécurité :**
- Le dépôt est public : `.env` est dans le `.gitignore`, et ni le jeton ni le mot de passe ne doivent
  apparaître dans le dépôt, dans un message ou sur une capture d'écran.
- Le jeton est un jeton **fine-grained**, limité à ce dépôt, avec le droit *Actions : lecture et
  écriture*, et une **date d'expiration**. Il se révoque dans les réglages GitHub.
- Sur Render, les variables se saisissent dans l'interface du service (*Environment*).

## 5. Déployer l'application sur Render

Plan gratuit : 512 Mo de mémoire, mise en veille après environ 15 minutes d'inactivité (le premier
affichage suivant prend un moment), disque éphémère. Les libellés de Render peuvent évoluer.

1. **New +**, puis **Web Service**.
2. Source : **Public Git Repository** (adresse du dépôt) ou **Git Provider** (compte GitHub relié).
3. Réglages :

| Champ | Valeur |
|---|---|
| Name | nom unique (il fixe l'adresse `https://<nom>.onrender.com`) |
| Region | Frankfurt (ou la région choisie pour l'équipe) |
| Branch | `master` |
| Language | Docker |
| Instance Type | Free |
| Environment Variables | `GITHUB_DEPOT`, `GITHUB_TOKEN`, `MOT_DE_PASSE_ADMIN` |

4. **Create Web Service**, puis suivre les *Logs* : la construction dure quelques minutes.

**Mises à jour.** Il y a deux modes, selon la façon dont le service est relié à GitHub :

| Source du service | Mise à jour après un commit |
|---|---|
| Public Git Repository | **manuelle** : *Manual Deploy*, puis *Deploy latest commit* |
| Git Provider (application GitHub de Render installée par le propriétaire du dépôt) | **automatique** (*Auto-Deploy On Commit*) |

Comme les modèles sont intégrés à l'image, **chaque réentraînement demande un redéploiement**.

## 6. L'API des modèles

Code : `src/api/app.py` (FastAPI). Tests : `tests/test_api.py`.

| Route | Rôle |
|---|---|
| `GET /sante` | vérifie que l'API répond |
| `GET /departements` | départements disponibles, par tâche, et version des modèles |
| `GET /modeles/{tache}/{departement}` | colonnes attendues, cible, métriques (`tache` : `classification` ou `regression`) |
| `POST /predict` | prédit l'étiquette DPE et la consommation (kWh/m²/an) |

FastAPI génère la documentation interactive sur `/docs` (et `/redoc`, `/openapi.json`).

`POST /predict` reçoit le département et une valeur par colonne attendue. Il appelle les deux modèles
(classification et régression) et renvoie :

```json
{"departement": "59", "etiquette_dpe": "D", "conso_kwh_m2_an": 170.5}
```

Erreurs : `404` (département ou tâche sans modèle), `422` (colonne manquante, qui est alors listée, ou
valeur invalide). Un exemple de requête complète est fourni : `docs/exemple_predict.json`.

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  --data-binary "@docs/exemple_predict.json"
```

Sous PowerShell, utiliser `curl.exe`.

### API sur Docker

Avec `docker compose up` (service `api`, port 8000), ou seule :

```bash
docker run --rm -p 8000:8000 sise-conso \
  python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` est indispensable dans un conteneur : sans lui, l'API n'écoute qu'à l'intérieur de
celui-ci.

### API sur Render

Même procédure que l'application (section 5), avec un **second service** construit sur la **même image
Docker** :

| Champ | Valeur |
|---|---|
| Name | différent de l'application (par exemple `sise-conso-api`) |
| Docker Command | python -m uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-10000} |
| Health Check Path | `/sante` |
| Environment Variables | aucune (l'API n'utilise pas de secret) |

Vérification :`https://<nom-du-service>.onrender.com/docs`.

## 7. Après un réentraînement

1. Le workflow `retrain.yml` se déclenche sur GitHub Actions depuis deux boutons protégés par mot de passe :
   « Relancer l'apprentissage » (page Prédiction, sans téléchargement) et « Rafraîchir les données »
   (page Contexte, nouveau téléchargement puis toute la pipeline, entrée `rafraichir` du workflow).
2. Le workflow rafraîchit les données si demandé, réentraîne les modèles, committe les résultats et
   met à jour `data/snapshot_actif.json` (version des données et des modèles affichées).
3. Il conserve les deux derniers snapshots et versions de modèles.
4. **Redéployer** l'application et l'API sur Render (automatique ou manuel, voir la section 5).

## 8. Dépannage

| Symptôme | Cause et solution |
|---|---|
| « Apprentissage non configuré » | variables d'environnement absentes : créer `.env` (local) ou les saisir dans Render, puis redémarrer |
| `ERR_ADDRESS_INVALID` sur `http://0.0.0.0:8000` | `0.0.0.0` n'est pas une adresse à ouvrir : utiliser `http://127.0.0.1:8000/docs` |
| `404` sur `http://127.0.0.1:8000/` | aucune route à la racine : ouvrir `/docs` |
| « port is already allocated » | un autre programme utilise le port : l'arrêter (`docker ps`, puis `docker stop <id>`) |
| Les liens locaux ne s'ouvrent pas | `docker compose up` doit tourner dans un terminal ; taper l'adresse dans le navigateur |
| Build Render : « No module named src.api » | le code de l'API n'est pas sur la branche déployée : fusionner la PR dans `master` |
| Render redémarre ou dépasse la mémoire | vérifier que l'allègement s'est exécuté à la construction (logs du build) |
| `422` sur `/predict` | colonne manquante ou valeur invalide : consulter `GET /modeles/{tache}/{departement}` |

## 9. Limites connues

- Plan gratuit de Render : veille automatique, 512 Mo de mémoire vive, disque éphémère.
- L'API n'a ni authentification ni limitation de débit (projet pédagogique).

