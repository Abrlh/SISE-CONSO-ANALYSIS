"""Graphiques Plotly. Chaque fonction reçoit un tableau déjà prêt et ne fait que le dessiner."""

import plotly.express as px

from affichage import COULEURS_ETIQUETTES, ETIQUETTES, NOMS_ORIGINES, NOMS_VARIABLES_COURTS, nom_departement

COULEURS = dict(zip(ETIQUETTES, COULEURS_ETIQUETTES))
VERT = "#0F766E"
ORANGE = "#F07F3C"
COULEURS_ORIGINES = {NOMS_ORIGINES["dpe_existants"]: VERT, NOMS_ORIGINES["dpe_neufs"]: ORANGE}

def _finir(fig, legende=True):
    """Mise en forme commune : marges serrées, hauteur fixe."""
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=360, legend_title_text="", showlegend=legende)
    return fig


def barres_etiquettes(tableau, y, titre, libelle_y):
    """Une barre par étiquette (couleurs DPE)."""
    fig = px.bar(
        tableau, x="etiquette", y=y, color="etiquette", color_discrete_map=COULEURS,
        category_orders={"etiquette": ETIQUETTES}, labels={"etiquette": "Étiquette", y: libelle_y}, title=titre,
    )
    return _finir(fig, legende=False)


def anneau(tableau, titre):
    """Poids de chaque étiquette."""
    fig = px.pie(
        tableau, names="etiquette", values="effectif", hole=0.5, color="etiquette",
        color_discrete_map=COULEURS, category_orders={"etiquette": ETIQUETTES}, title=titre,
    )
    return _finir(fig)


def histogramme(tableau, titre):
    """Distribution de la consommation : une barre par tranche (début de tranche en abscisse)."""
    fig = px.bar(
        tableau, x="borne_min", y="effectif", title=titre,
        labels={"borne_min": "Consommation, début de tranche (kWh/m²/an)", "effectif": "Nombre de logements"},
        color_discrete_sequence=[VERT],
    )
    fig.update_layout(bargap=0)
    return _finir(fig, legende=False)


def conso_par_energie(tableau, titre):
    """Consommation médiane par étiquette, une couleur par famille d'énergie."""
    fig = px.bar(
        tableau, x="etiquette", y="mediane", color="famille_energie", barmode="group",
        category_orders={"etiquette": ETIQUETTES}, title=titre,
        labels={"etiquette": "Étiquette", "mediane": "Consommation médiane (kWh/m²/an)"},
        hover_data=["effectif", "q1", "q3"],
    )
    return _finir(fig)


def barres_modalites(tableau, titre):
    """Consommation médiane pour chaque modalité d'une caractéristique."""
    fig = px.bar(
        tableau, x="modalite", y="mediane", title=titre, hover_data=["effectif", "q1", "q3", "part_f_g"],
        labels={"modalite": "", "mediane": "Consommation médiane (kWh/m²/an)"}, color_discrete_sequence=[VERT],
    )
    return _finir(fig, legende=False)


def barres_empilees(tableau, titre):
    """Répartition des étiquettes dans chaque modalité."""
    fig = px.bar(
        tableau, x="modalite", y="pourcentage", color="etiquette", color_discrete_map=COULEURS,
        category_orders={"etiquette": ETIQUETTES}, title=titre, labels={"modalite": "", "pourcentage": "% des logements"},
    )
    return _finir(fig)


def chaleur(tableau, titre):
    """Étiquette GES selon l'étiquette DPE (pourcentage par ligne)."""
    grille = tableau.pivot(index="etiquette_dpe", columns="etiquette_ges", values="pourcentage")
    grille = grille.reindex(index=ETIQUETTES, columns=ETIQUETTES)
    fig = px.imshow(
        grille, text_auto=".0f", aspect="auto", color_continuous_scale="Teal", title=titre,
        labels={"x": "Étiquette GES", "y": "Étiquette DPE", "color": "% par ligne"},
    )
    return _finir(fig, legende=False)


def courbe(tableau, y, titre, libelle_y):
    """Évolution d'une valeur selon l'année de réception du DPE."""
    fig = px.line(tableau, x="annee", y=y, markers=True, title=titre, labels={"annee": "Année", y: libelle_y})
    fig.update_xaxes(type="category")
    return _finir(fig, legende=False)


def barres_annuelles(tableau, titre):
    """Nombre de logements par année de réception."""
    fig = px.bar(
        tableau, x="annee", y="effectif", title=titre, labels={"annee": "Année", "effectif": "Nombre de logements"},
        color_discrete_sequence=[VERT],
    )
    fig.update_xaxes(type="category")
    return _finir(fig, legende=False)


def barres_manquants(tableau, titre):
    """Part de cases vides par colonne (barres horizontales)."""
    fig = px.bar(
        tableau, x="pct_manquant", y="colonne", orientation="h", title=titre,
        labels={"pct_manquant": "% de cases vides", "colonne": ""}, color_discrete_sequence=[VERT],
    )
    fig.update_yaxes(autorange="reversed")
    return _finir(fig, legende=False)

def matrice_correlation(tableau, titre):
    """Matrice de corrélation entre les variables numériques : la valeur est écrite dans chaque case."""
    ordre = list(NOMS_VARIABLES_COURTS.values())
    grille = tableau.pivot(index="variable_y", columns="variable_x", values="correlation")
    grille = grille.reindex(index=ordre, columns=ordre)
    fig = px.imshow(
        grille, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", zmin=-1, zmax=1, title=titre,
        labels={"x": "", "y": "", "color": "Corrélation"},
    )
    return _finir(fig, legende=False)

def camembert_ges(tableau, titre):
    """Répartition des logements par étiquette GES (camembert). Plotly regroupe les effectifs par étiquette."""
    fig = px.pie(
        tableau, names="etiquette_ges", values="effectif", color="etiquette_ges",
        color_discrete_map=COULEURS, category_orders={"etiquette_ges": ETIQUETTES}, title=titre,
    )
    return _finir(fig)

def histogramme_origines(tableau, titre):
    """Distribution de la consommation : logements existants et neufs superposés (% de chaque origine)."""
    tableau = tableau.assign(origine=tableau["origine"].astype(str).map(lambda code: NOMS_ORIGINES.get(code, code)))
    fig = px.bar(
        tableau, x="borne_min", y="pourcentage", color="origine", barmode="overlay", opacity=0.65,
        color_discrete_map=COULEURS_ORIGINES, title=titre,
        labels={"borne_min": "Consommation, début de tranche (kWh/m²/an)", "pourcentage": "% des logements de l'origine"},
    )
    # Chaque barre fait 20 de large (tranches de 20 kWh/m²/an) et commence au début de la tranche
    fig.update_traces(width=20, offset=0)
    fig.update_layout(bargap=0)
    return _finir(fig)

def nuage_surface_conso(tableau, titre):
    """Un point par logement de l'échantillon : consommation selon la surface, couleur = étiquette DPE."""
    fig = px.scatter(
        tableau, x="surface_habitable_logement", y="conso_5_usages_par_m2_ep", color="etiquette_dpe",
        color_discrete_map=COULEURS, category_orders={"etiquette_dpe": ETIQUETTES}, opacity=0.7, title=titre,
        labels={"surface_habitable_logement": "Surface habitable (m²)",
                "conso_5_usages_par_m2_ep": "Consommation (kWh/m²/an)", "etiquette_dpe": "Étiquette"},
    )
    fig.update_traces(marker=dict(size=5))
    return _finir(fig)


def barres_departements(tableau, y, titre, libelle_y, format_texte=".0f"):
    """Une paire de barres (existants / neufs) par département."""
    # On retire les lignes « Tous » : on veut comparer les départements entre eux
    tableau = tableau[(tableau["departement"].astype(str) != "Tous") & (tableau["origine"].astype(str) != "Tous")].copy()
    tableau["departement"] = tableau["departement"].astype(str).map(nom_departement)
    tableau["origine"] = tableau["origine"].astype(str).map(lambda code: NOMS_ORIGINES.get(code, code))
    fig = px.bar(
        tableau, x="departement", y=y, color="origine", barmode="group", text_auto=format_texte,
        color_discrete_map=COULEURS_ORIGINES, title=titre, labels={"departement": "", y: libelle_y},
    )
    return _finir(fig)

COULEURS_ENERGIES = {
    "Électricité": "#F07F3C", "Gaz naturel": "#F4B942", "Fioul": "#C0392B",
    "Bois": "#8B5E3C", "Réseau de chaleur": "#0F766E", "Autre": "#8D99AE",
}


def courbes_energie(tableau, titre):
    """Une courbe par énergie de chauffage : consommation médiane selon l'étiquette."""
    tableau = tableau[tableau["famille_energie"].astype(str) != "Tous"].copy()
    tableau = tableau.sort_values("etiquette", key=lambda colonne: colonne.astype(str).map(ETIQUETTES.index))
    fig = px.line(
        tableau, x="etiquette", y="mediane", color="famille_energie", markers=True,
        color_discrete_map=COULEURS_ENERGIES, category_orders={"etiquette": ETIQUETTES},
        hover_data=["effectif", "q1", "q3"], title=titre,
        labels={"etiquette": "Étiquette DPE", "mediane": "Consommation médiane (kWh/m²/an)", "famille_energie": "Énergie"},
    )
    return _finir(fig)