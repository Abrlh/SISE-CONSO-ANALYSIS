import pandas as pd

from ..preprocessing import verifier_colonnes

CIBLE_CLASSIFICATION = "etiquette_dpe"
CIBLE_REGRESSION = "conso_5_usages_par_m2_ef"

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
    """Sépare les variables d'entrée X (variables du formulaire) et la cible y.

    Raises:
        ColonnesManquantesError: une variable du formulaire ou la cible manque (comme au nettoyage)
    """
    verifier_colonnes(df, VARIABLES_FORMULAIRE + [cible], "Variables du formulaire ou cible")
    return df[VARIABLES_FORMULAIRE], df[cible]
