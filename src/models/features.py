"""
Choix des colonnes d'entrée des modèles (repris de la cellule 1.1.3 du notebook 03_ML).
Les mêmes colonnes sont retirées pour la classification et la régression.
"""
import pandas as pd

# sorties du calcul DPE : les garder revient à donner la réponse au modèle
PREFIXES_FUITE = ("conso_", "cout_", "emission_ges", "besoin_", "etiquette_")
# identifiants : une valeur (presque) unique par ligne
ID_LIST = ["numero_dpe", "_id", "_i", "_rand", "identifiant_ban", "id_rnb"]
# adresses et localisation : on prédit à partir du logement, pas de son emplacement
LOCALISATION_LIST = ["adresse_ban", "adresse_brut", "adresse_complete_brut", "complement_adresse_batiment",
                     "complement_adresse_logement", "nom_rue_ban", "numero_voie_ban",
                     "code_postal_ban", "code_postal_brut", "code_insee_ban", "nom_commune_ban", "nom_commune_brut",
                     "code_departement_ban", "code_region_ban", "coordonnee_cartographique_x_ban",
                     "coordonnee_cartographique_y_ban", "latitude", "longitude", "score_ban", "statut_geocodage"]
# informations sur le diagnostic lui-même, pas sur le logement
INFO_DPE_LIST = ["modele_dpe", "version_dpe", "methode_application_dpe", "origine", "provenance_id_rnb",
                 "appartement_non_visite"]
# dates du diagnostic (l'âge du logement reste dans annee_construction / periode_construction)
DATE_LIST = ["date_etablissement_dpe", "date_reception_dpe", "date_fin_validite_dpe",
             "date_visite_diagnostiqueur", "date_derniere_modification_dpe"]


def colonnes_a_retirer(df:pd.DataFrame)-> list[str]:
    """Colonnes de df qui ne doivent pas servir d'entrée à un modèle."""
    fuite = [c for c in df.columns if c.startswith(PREFIXES_FUITE)]
    # descriptions en texte libre, redondantes avec les colonnes type_*
    description = [c for c in df.columns if c.startswith("description_")]
    liste = fuite + ID_LIST + LOCALISATION_LIST + description + INFO_DPE_LIST + DATE_LIST
    return [c for c in liste if c in df.columns]


def preparer_xy(df:pd.DataFrame, cible:str)-> tuple[pd.DataFrame, pd.Series]:
    """Sépare les variables d'entrée X et la cible y (la cible est aussi retirée de X)."""
    y = df[cible]
    X = df.drop(columns=list(dict.fromkeys(colonnes_a_retirer(df) + [cible])))
    return X, y
