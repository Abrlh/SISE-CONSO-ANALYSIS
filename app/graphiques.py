"""Graphiques Plotly. Chaque fonction reçoit un tableau déjà prêt et ne fait que le dessiner."""

import plotly.express as px

from affichage import COULEURS_ETIQUETTES, ETIQUETTES

COULEURS = dict(zip(ETIQUETTES, COULEURS_ETIQUETTES))
VERT = "#0F766E"


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
    fig = px.density_heatmap(
        tableau, x="etiquette_ges", y="etiquette_dpe", z="pourcentage", histfunc="sum", title=titre,
        category_orders={"etiquette_ges": ETIQUETTES, "etiquette_dpe": ETIQUETTES},
        labels={"etiquette_ges": "Étiquette GES", "etiquette_dpe": "Étiquette DPE"}, color_continuous_scale="Teal",
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
