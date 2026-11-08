"""Éléments d'affichage partagés par les pages."""

import streamlit as st

# Étiquettes DPE de A (très performant) à G (très énergivore)
ETIQUETTES = ["A", "B", "C", "D", "E", "F", "G"]

# Couleurs des étiquettes, de A (vert) à G (rouge), dans le même ordre que ETIQUETTES
COULEURS_ETIQUETTES = ["#319834", "#33cc31", "#cbfc34", "#fbfe06", "#fccc05", "#fc9935", "#fc0205"]

# Noms des départements du projet
NOMS_DEPARTEMENTS = {"59": "Nord", "69": "Rhône", "75": "Paris"}
# Noms lisibles des origines des logements (affichage seulement)
NOMS_ORIGINES = {"dpe_existants": "Logements existants", "dpe_neufs": "Logements neufs"}

NOMS_VARIABLES_NUMERIQUES = {
    "conso_5_usages_par_m2_ef": "Consommation d'énergie finale",
    "surface_habitable_logement": "Surface habitable du logement (m²)",
    "hauteur_sous_plafond": "Hauteur sous plafond (m)",
    "emission_ges_5_usages_par_m2": "Émissions de gaz à effet de serre de 5 usages par m² (kg CO₂e/m²/an)",
    "cout_total_5_usages": "Coût total de l'énergie de 5 usages (€/an)",
}

# Noms courts des variables numériques, pour les axes des graphiques
NOMS_VARIABLES_COURTS = {
    "conso_5_usages_par_m2_ef": "Consommation d'énergie finale",
    "surface_habitable_logement": "Surface<br>habitable",
    "hauteur_sous_plafond": "Hauteur sous<br>plafond",
    "emission_ges_5_usages_par_m2": "Émissions de GES<br>(5 usages)",
    "cout_total_5_usages": "Coût de l'énergie<br>(5 usages)",
}

NOMS_COLONNES_STATS = {
    "variable": "Variable", "effectif": "Effectif", "nb_manquants": "Valeurs manquantes",
    "moyenne": "Moyenne", "ecart_type": "Écart-type", "minimum": "Minimum", "p05": "Percentile 5",
    "q1": "Quartile 1", "mediane": "Médiane", "q3": "Quartile 3", "p95": "Percentile 95", "maximum": "Maximum",
}

# Titres lisibles des colonnes de l'aperçu des données
NOMS_COLONNES_APERCU = {
    "departement": "Département",
    "origine": "Origine",
    "etiquette_dpe": "Étiquette DPE",
    "conso_5_usages_par_m2_ef": NOMS_VARIABLES_NUMERIQUES["conso_5_usages_par_m2_ef"],
    "surface_habitable_logement": NOMS_VARIABLES_NUMERIQUES["surface_habitable_logement"],
    "periode_construction": "Période de construction",
    "type_batiment": "Type de bâtiment",
    "type_energie_principale_chauffage": "Énergie principale de chauffage",
    "famille_energie": "Famille d'énergie",
    "tranche_surface": "Tranche de surface",
    "qualite_isolation_enveloppe": "Qualité de l'isolation",
    "annee_reception": "Année de réception",
    "code_insee_ban": "Code INSEE",
    "nom_commune_ban": "Commune",
    "latitude": "Latitude",
    "longitude": "Longitude",
}


def nom_departement(code):
    """Nom lisible d'un département, ex. '59' -> 'Nord (59)'."""
    return f"{NOMS_DEPARTEMENTS.get(code, code)} ({code})"


def liste_valeurs(tableau, colonne):
    """Valeurs distinctes d'une colonne, triées, sans la valeur « Tous »."""
    return sorted(v for v in tableau[colonne].astype(str).unique() if v != "Tous")


def filtres_perimetre(conteneur, tableau_perimetres):
    """Affiche les filtres Département et Origine, d'après un tableau qui a ces deux colonnes (kpi_globaux).

    Renvoie (département, origine). La valeur « Tous » veut dire « tous confondus ».
    """
    departement = conteneur.selectbox(
        "Département",
        ["Tous"] + liste_valeurs(tableau_perimetres, "departement"),
        format_func=lambda code: code if code == "Tous" else nom_departement(code),
    )
    origine = conteneur.radio("Origine du logement", ["Tous"] + liste_valeurs(tableau_perimetres, "origine"))
    return departement, origine


def choisir(tableau, departement=None, origine=None):
    """Sélectionne les lignes d'un tableau pour un département et/ou une origine. Aucun calcul."""
    masque = tableau.index == tableau.index
    if departement is not None and "departement" in tableau.columns:
        masque = masque & (tableau["departement"].astype(str) == departement)
    if origine is not None and "origine" in tableau.columns:
        masque = masque & (tableau["origine"].astype(str) == origine)
    return tableau[masque]


def fmt_nombre(valeur, decimales=0):
    """Met un nombre en forme à la française (388717 -> '388 717')."""
    return f"{valeur:,.{decimales}f}".replace(",", " ")


def legende_etiquettes():
    """Légende des couleurs des étiquettes, en une ligne."""
    elements = [
        "<span style='display:inline-block;width:12px;height:12px;border-radius:50%;"
        f"background:{couleur};margin-right:4px'></span>{lettre}"
        for lettre, couleur in zip(ETIQUETTES, COULEURS_ETIQUETTES)
    ]
    st.markdown("&nbsp;&nbsp;&nbsp;".join(elements), unsafe_allow_html=True)


# ---- Formulaire de la page Prédiction (affichage seulement : les champs viennent des modèles)
# colonne du modèle -> libellé lisible
NOMS_CHAMPS = {
    "surface_habitable_logement": "Surface habitable (m²)",
    "annee_construction": "Année de construction",
    "type_batiment": "Type de bâtiment",
    "nombre_niveau_logement": "Nombre de niveaux",
    "numero_etage_appartement": "Étage de l'appartement",
    "zone_climatique": "Zone climatique",
    "classe_altitude": "Classe d'altitude",
    "type_energie_n1": "Énergie principale de chauffage",
    "type_energie_n2": "Énergie secondaire de chauffage",
    "type_generateur_n1_installation_n1": "Générateur de chauffage",
    "type_emetteur_installation_chauffage_n1": "Émetteur de chaleur",
    "type_installation_ecs": "Installation d'eau chaude",
    "type_generateur_n1_ecs_n1": "Générateur d'eau chaude",
    "type_ventilation": "Type de ventilation",
    "qualite_isolation_enveloppe": "Isolation de l'enveloppe",
    "qualite_isolation_murs": "Isolation des murs",
    "qualite_isolation_plancher_haut_comble_perdu": "Isolation du plancher haut (comble perdu)",
    "qualite_isolation_plancher_bas": "Isolation du plancher bas",
    "qualite_isolation_menuiseries": "Isolation des menuiseries",
    "isolation_toiture": "Isolation de la toiture",
}

# cartes du formulaire : (titre, icône Material, colonnes du modèle)
GROUPES_CHAMPS = [
    ("Logement", "apartment", ["surface_habitable_logement", "annee_construction", "type_batiment",
                               "nombre_niveau_logement", "numero_etage_appartement"]),
    ("Localisation", "location_on", ["zone_climatique", "classe_altitude"]),
    ("Chauffage", "local_fire_department", ["type_energie_n1", "type_energie_n2",
                                            "type_generateur_n1_installation_n1",
                                            "type_emetteur_installation_chauffage_n1"]),
    ("Eau chaude", "water_drop", ["type_installation_ecs", "type_generateur_n1_ecs_n1"]),
    ("Ventilation", "air", ["type_ventilation"]),
    ("Isolation", "layers", ["qualite_isolation_enveloppe", "qualite_isolation_murs",
                             "qualite_isolation_plancher_haut_comble_perdu", "qualite_isolation_plancher_bas",
                             "qualite_isolation_menuiseries", "isolation_toiture"]),
]

# champs numériques qui se saisissent en nombres entiers (pas de décimales à l'écran)
CHAMPS_ENTIERS = {"annee_construction", "nombre_niveau_logement", "numero_etage_appartement"}

# phrase sous le titre de chaque étape du formulaire (page Prédiction, affichage seulement)
DESCRIPTIONS_GROUPES = {
    "Logement": "Taille, âge et type du bâtiment",
    "Localisation": "Où se trouve le logement",
    "Chauffage": "Énergie et équipements de chauffage",
    "Eau chaude": "Production d'eau chaude sanitaire",
    "Ventilation": "Renouvellement de l'air",
    "Isolation": "Murs, toiture, plancher et fenêtres",
    "Autres caractéristiques": "Les autres informations demandées par les modèles",
}