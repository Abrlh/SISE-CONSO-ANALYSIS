# Description

# Lancement

Toutes les commandes se lancent depuis la racine du dépôt (`SISE-CONSO-ANALYSIS/`).

```bash
python3 -m venv .venv && source .venv/bin/activate   # première fois
pip install -r requirements.txt

python -m src.orchestration.train              # entraînement (télécharge les données si aucun snapshot)
python -m src.orchestration.train --refresh    # idem avec nouveau téléchargement
streamlit run app/main.py        # application
```
