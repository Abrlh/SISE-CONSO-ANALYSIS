"""Prépare data/ et models/ pour l'image Docker (plan Render gratuit, 512 Mo).

1. Retient le snapshot COMPLET le plus récent : présent à la fois dans models/,
   data/processed/ et data/stats/.
2. Supprime les autres snapshots, dans l'image uniquement.
3. Réduit data/processed aux colonnes utilisées par les modèles (meta.json).

Sans option : simple simulation. Avec --ecrire : modifie les fichiers.
Réservé à la construction de l'image (variable ALLEGER_DOCKER=1).
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import pyarrow.parquet as pq

RACINE = Path(__file__).resolve().parent.parent
MODELES = RACINE / "models"
PROCESSED = RACINE / "data" / "processed"
STATS = RACINE / "data" / "stats"


def snapshots(dossier):
    """Noms des sous-dossiers (un par snapshot) ; vide si le dossier n'existe pas."""
    if not dossier.exists():
        return set()
    return {p.name for p in dossier.iterdir() if p.is_dir()}


def choisir_snapshot():
    modeles, processed, stats = snapshots(MODELES), snapshots(PROCESSED), snapshots(STATS)
    complets = sorted(modeles & processed & stats)
    if not complets:
        sys.exit("Aucun snapshot complet (modèles + données prétraitées + statistiques).\n"
                 f"  models/         : {sorted(modeles)}\n"
                 f"  data/processed/ : {sorted(processed)}\n"
                 f"  data/stats/     : {sorted(stats)}")
    retenu = complets[-1]
    for nom in sorted(modeles | processed | stats):
        if nom == retenu:
            continue
        manque = [lieu for lieu, ens in (("models", modeles), ("processed", processed),
                                         ("stats", stats)) if nom not in ens]
        raison = f"incomplet (manque : {', '.join(manque)})" if manque else "plus ancien"
        print(f"Ignoré : {nom} -> {raison}")
    print(f"Retenu : {retenu}")
    return retenu


def colonnes_utiles(snapshot):
    """{département: colonnes à garder}, d'après models/<snapshot>/*/*/meta.json."""
    utiles = {}
    for chemin in sorted((MODELES / snapshot).glob("*/*/meta.json")):
        meta = json.loads(chemin.read_text(encoding="utf-8"))
        cols = utiles.setdefault(str(meta["departement"]), set())
        cols.update(meta["colonnes"])
        if meta.get("cible"):
            cols.add(meta["cible"])
    return utiles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ecrire", action="store_true",
                        help="modifie les fichiers (à n'utiliser que dans l'image Docker)")
    args = parser.parse_args()

    if args.ecrire and os.environ.get("ALLEGER_DOCKER") != "1":
        sys.exit("Refusé : --ecrire modifierait tes fichiers du dépôt. "
                 "Il ne doit tourner que pendant la construction de l'image.")

    retenu = choisir_snapshot()
    utiles = colonnes_utiles(retenu)
    if not utiles:
        sys.exit(f"Aucun meta.json de modèle dans models/{retenu}.")

    # Vérifications avant toute modification
    plan = []
    for dept, cols in sorted(utiles.items()):
        fichier = PROCESSED / retenu / f"{dept}.parquet"
        if not fichier.exists():
            sys.exit(f"Introuvable : {fichier}")
        presentes = pq.read_schema(fichier).names
        absentes = sorted(cols - set(presentes))
        if absentes:
            sys.exit(f"{retenu}/{dept} : colonnes demandées par les modèles "
                     f"mais absentes des données : {absentes}")
        a_garder = [c for c in presentes if c in cols]
        print(f"{retenu}/{dept} : {len(presentes)} colonnes -> {len(a_garder)}")
        plan.append((fichier, a_garder))

    if not args.ecrire:
        print("Simulation : rien n'a été modifié.")
        return

    for dossier in (MODELES, PROCESSED, STATS):
        for nom in snapshots(dossier) - {retenu}:
            shutil.rmtree(dossier / nom)
    for fichier, a_garder in plan:
        table = pq.read_table(fichier, columns=a_garder)
        temporaire = fichier.with_suffix(".tmp")
        pq.write_table(table, temporaire)
        temporaire.replace(fichier)
    print("Terminé.")


if __name__ == "__main__":
    main()