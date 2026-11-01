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

# Illustration de la page d'accueil : une maison et l'échelle des étiquettes
ILLUSTRATION_SVG = """
<svg viewBox="0 0 340 220" width="100%" role="img" aria-label="Maison et échelle des étiquettes DPE de A à G">
  <path d="M20 120 100 50l80 70v80H20z" fill="#FFFFFF" stroke="#0F766E" stroke-width="3" stroke-linejoin="round"/>
  <rect x="82" y="150" width="36" height="50" fill="#0F766E"/>
  <rect x="44" y="124" width="28" height="24" fill="#BFD9D4"/>
  <rect x="128" y="124" width="28" height="24" fill="#BFD9D4"/>
  <rect x="200" y="30" width="60" height="20" rx="3" fill="#319834"/>
  <rect x="200" y="54" width="75" height="20" rx="3" fill="#33CC31"/>
  <rect x="200" y="78" width="90" height="20" rx="3" fill="#CBFC34"/>
  <rect x="200" y="102" width="105" height="20" rx="3" fill="#FBFE06"/>
  <rect x="200" y="126" width="120" height="20" rx="3" fill="#FBCC05"/>
  <rect x="200" y="150" width="120" height="20" rx="3" fill="#FC9935"/>
  <rect x="200" y="174" width="120" height="20" rx="3" fill="#FC0205"/>
</svg>
"""

NOMS_VARIABLES_NUMERIQUES = {
    "conso_5_usages_par_m2_ep": "Consommation d'énergie de 5 usages par m² (kWh/m²/an)",
    "surface_habitable_logement": "Surface habitable du logement (m²)",
    "hauteur_sous_plafond": "Hauteur sous plafond (m)",
    "emission_ges_5_usages_par_m2": "Émissions de gaz à effet de serre de 5 usages par m² (kg CO₂e/m²/an)",
    "cout_total_5_usages": "Coût total de l'énergie de 5 usages (€/an)",
}

# Noms courts des variables numériques, pour les axes des graphiques
NOMS_VARIABLES_COURTS = {
    "conso_5_usages_par_m2_ep": "Consommation d'énergie<br>(5 usages)",
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
    "conso_5_usages_par_m2_ep": NOMS_VARIABLES_NUMERIQUES["conso_5_usages_par_m2_ep"],
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
        f"<span style='display:inline-block;width:12px;height:12px;border-radius:50%;"
        f"background:{couleur};margin-right:4px'></span>{lettre}"
        for lettre, couleur in zip(ETIQUETTES, COULEURS_ETIQUETTES)
    ]
    st.markdown("&nbsp;&nbsp;&nbsp;".join(elements), unsafe_allow_html=True)


def a_venir(titre, detail="Ce graphique sera affiché avec les résultats préparés par le back end."):
    """Emplacement d'un graphique ou d'un chiffre qui sera branché plus tard."""
    with st.container(border=True):
        st.markdown(f"**{titre}**")
        st.caption(f"À venir. {detail}")
