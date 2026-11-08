"""Allège data/processed pour l'image Docker (plan Render gratuit, 512 Mo).

Pour chaque (snapshot, département), garde uniquement les colonnes utilisées
par les modèles (meta.json) et leurs cibles. Sans option : simple simulation.
Avec --ecrire : réécrit les fichiers. Réservé à la construction de l'image.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import pyarrow.parquet as pq

RACINE = Path(__file__).resolve().parent.parent


def colonnes_utiles():
    """{(snapshot, département): colonnes à garder}, d'après models/*/*/*/meta.json."""
    utiles = {}
    for chemin in sorted((RACINE / "models").glob("*/*/*/meta.json")):
        meta = json.loads(chemin.read_text(encoding="utf-8"))
        cle = (meta["snapshot_id"], str(meta["departement"]))
        cols = utiles.setdefault(cle, set())
        cols.update(meta["colonnes"])
        if meta.get("cible"):
            cols.add(meta["cible"])
    return utiles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ecrire", action="store_true",
                        help="réécrit les fichiers (à n'utiliser que dans l'image Docker)")
    args = parser.parse_args()

    if args.ecrire and os.environ.get("ALLEGER_DOCKER") != "1":
        sys.exit("Refusé : --ecrire modifierait tes fichiers du dépôt. "
                 "Il ne doit tourner que pendant la construction de l'image.")

    utiles = colonnes_utiles()
    if not utiles:
        sys.exit("Aucun meta.json de modèle trouvé dans models/.")

    for (snapshot, dept), cols in sorted(utiles.items()):
        fichier = RACINE / "data" / "processed" / snapshot / f"{dept}.parquet"
        if not fichier.exists():
            sys.exit(f"Introuvable : {fichier} (modèles et données prétraitées "
                     f"doivent être du même snapshot)")
        presentes = pq.read_schema(fichier).names
        a_garder = [c for c in presentes if c in cols]
        absentes = sorted(cols - set(presentes))
        if absentes:
            sys.exit(f"{snapshot}/{dept} : colonnes demandées par les modèles "
                     f"mais absentes des données : {absentes}")
        print(f"{snapshot}/{dept} : {len(presentes)} colonnes -> {len(a_garder)}")
        if args.ecrire:
            table = pq.read_table(fichier, columns=a_garder)
            temporaire = fichier.with_suffix(".tmp")
            pq.write_table(table, temporaire)
            temporaire.replace(fichier)

    print("Terminé." if args.ecrire else "Simulation : rien n'a été modifié.")


if __name__ == "__main__":
    main()