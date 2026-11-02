"""
Les modèles ne sont entraînés que sur les variables du formulaire de l'application : le score mesuré
au test est celui que le formulaire obtiendra. Mêmes variables pour la classification et la régression.
Les préfixes sont utilisés par l'audit des colonnes (src/audit_colonnes.py) : une seule liste.
"""
import pandas as pd

PREFIXES_FUITE = ("conso_", "cout_", "emission_ges", "besoin", "etiquette_", "production_", "indicateur_")

PREFIXES_CALCUL = ("deperditions", "ubat", "apport_")

BASE_FORMULAIRE = [
    "surface_habitable_logement", "annee_construction", "type_batiment",
    "zone_climatique", "classe_altitude",
    "nombre_niveau_logement", "numero_etage_appartement",
    "type_energie_n1", "type_energie_n2", "type_generateur_n1_installation_n1",
    "type_emetteur_installation_chauffage_n1",
    "type_installation_ecs", "type_generateur_n1_ecs_n1", "type_ventilation",
]

ISOLATION_PERCUE = [
    "qualite_isolation_enveloppe", "qualite_isolation_murs",
    "qualite_isolation_plancher_haut_comble_perdu", "qualite_isolation_plancher_bas",
    "qualite_isolation_menuiseries", "isolation_toiture",
]
VARIABLES_FORMULAIRE = BASE_FORMULAIRE + ISOLATION_PERCUE


def preparer_xy(df:pd.DataFrame, cible:str)-> tuple[pd.DataFrame, pd.Series]:
    """Sépare les variables d'entrée X (variables du formulaire présentes dans df) et la cible y."""
    y = df[cible]
    X = df[[c for c in VARIABLES_FORMULAIRE if c in df.columns]]
    return X, y
