# Description

# Lancement

Toutes les commandes se lancent depuis la racine du dépôt (`SISE-CONSO-ANALYSIS/`).

```bash
python3 -m venv .venv && source .venv/bin/activate   # première fois
pip install -r requirements.txt

python -m src.train              # entraînement (télécharge les données si aucun snapshot)
python -m src.train --refresh    # idem avec nouveau téléchargement
streamlit run app/main.py        # application
```
## Nettoyage des données

1. Cloner le dépôt puis, à la racine du projet, créer l'environnement Python :
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt

2. Générer les données propres (obligatoire après chaque clone ou pull) :
   python -m src.train --snapshot 2026-10-12_132605 --preprocess

   Cette commande lit data/raw/ et écrit data/processed/, en écrasant les
   anciens fichiers.

Détails du nettoyage : docs/nettoyage_donnees.md
