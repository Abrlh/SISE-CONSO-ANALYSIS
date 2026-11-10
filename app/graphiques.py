"""Graphiques Plotly. Chaque fonction reçoit un tableau déjà prêt et ne fait que le dessiner."""

import plotly.express as px
import plotly.graph_objects as go

from affichage import (
    COULEURS_ETIQUETTES, ETIQUETTES, NOMS_ORIGINES, NOMS_VARIABLES_COURTS, nom_departement,
)

COULEURS = dict(zip(ETIQUETTES, COULEURS_ETIQUETTES))
VERT = "#428B49"
ORANGE = "#FC9935"
COULEURS_ORIGINES = {NOMS_ORIGINES["dpe_existants"]: ORANGE, NOMS_ORIGINES["dpe_neufs"]: VERT}


def _finir(fig, legende=True):
    """Mise en forme commune : marges serrées, hauteur fixe."""
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=360, legend_title_text="", showlegend=legende)
    return fig

def _habiller(fig):
    """Style commun des graphiques : fond transparent, quadrillage clair, titre aligné à gauche
    (couleurs de l'interface)."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        title=dict(x=0, font=dict(size=17, color="#17301B")),
    )
    fig.update_xaxes(showline=True, linecolor="#E3EFCF")
    fig.update_yaxes(gridcolor="#E3EFCF", zeroline=False)
    return fig


def _habiller_origines(fig, bas=60, y_legende=-0.12):
    """Style des graphiques « logements existants / neufs » : le style commun, avec la légende
    horizontale sous le graphique.

    bas : marge sous le graphique (px) ; y_legende : position de la légende, à descendre
    quand l'axe horizontal a un titre.
    """
    fig = _habiller(fig)
    fig.update_layout(
        margin=dict(l=10, r=10, t=50, b=bas),
        legend=dict(orientation="h", yanchor="top", y=y_legende, xanchor="center", x=0.5),
    )
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

def barres_modalites(tableau, titre):
    """Consommation médiane pour chaque modalité d'une caractéristique."""
    # le titre du graphique dit déjà « consommation médiane » : l'axe ne garde que l'unité
    fig = px.bar(
        tableau, x="modalite", y="mediane", title=titre, hover_data=["effectif", "q1", "q3", "part_f_g"],
        labels={"modalite": "", "mediane": "kWh/m²/an"}, color_discrete_sequence=[VERT],
    )
    fig.update_traces(marker_cornerradius=8)
    fig.update_layout(bargap=0.35)
    return _habiller(_finir(fig, legende=False))

def barres_empilees(tableau, titre):
    """Répartition des étiquettes dans chaque modalité."""
    fig = px.bar(
        tableau, x="modalite", y="pourcentage", color="etiquette", color_discrete_map=COULEURS,
        category_orders={"etiquette": ETIQUETTES}, title=titre, labels={"modalite": "", "pourcentage": "% des logements"},
    )
    fig.update_layout(bargap=0.35)
    return _habiller(_finir(fig))


def ges_selon_dpe(tableau, titre):
    """Étiquette GES des logements de chaque étiquette DPE : une barre par étiquette DPE, découpée par GES."""
    # Un pourcentage par case (DPE, GES) : le tableau est mis en grille avec une ligne par étiquette DPE.
    cases = tableau.pivot_table(
        index="etiquette_dpe", columns="etiquette_ges", values="pourcentage", aggfunc="sum"
    ).reindex(index=ETIQUETTES, columns=ETIQUETTES).fillna(0)
    fig = go.Figure()
    for ges in ETIQUETTES:
        valeurs = cases[ges]
        fig.add_bar(
            y=ETIQUETTES, x=valeurs, orientation="h", name=ges, marker_color=COULEURS[ges],
            text=[f"{v:.0f}" if v >= 6 else "" for v in valeurs], textposition="inside", textangle=0,
            textfont=dict(color="#FFFFFF" if ges in ("A", "G") else "#17301B"),
            hovertemplate=f"DPE %{{y}} : %{{x:.0f}} % ont une étiquette GES {ges}<extra></extra>",
        )
    fig = _finir(fig)
    fig.update_layout(
        barmode="stack", bargap=0.25, title=titre, margin=dict(l=10, r=10, t=50, b=70),
        legend=dict(orientation="h", x=0, y=-0.25, title_text="Étiquette GES", traceorder="normal"),
    )
    fig.update_yaxes(autorange="reversed", title="Étiquette DPE")
    fig.update_xaxes(range=[0, 100], title="% des logements de l'étiquette DPE")
    return fig


def courbe(tableau, y, titre, libelle_y, couleur=VERT):
    """Évolution d'une valeur selon l'année de réception du DPE."""
    fig = px.line(tableau, x="annee", y=y, markers=True, title=titre, labels={"annee": "Année", y: libelle_y})
    fig.update_xaxes(type="category")
    # trait plus épais, points ronds cerclés de blanc ; la courbe reste droite entre les points (pas de lissage)
    fig.update_traces(line=dict(width=3, color=couleur),
                      marker=dict(size=9, color=couleur, line=dict(width=2, color="#FFFFFF")))
    return _habiller(_finir(fig, legende=False))


def barres_annuelles(tableau, titre):
    """Nombre de logements par année de réception."""
    fig = px.bar(
        tableau, x="annee", y="effectif", title=titre, labels={"annee": "Année", "effectif": "Nombre de logements"},
        color_discrete_sequence=[VERT],
    )
    fig.update_xaxes(type="category")
    fig.update_traces(marker_cornerradius=8)
    fig.update_layout(bargap=0.35)
    return _habiller(_finir(fig, legende=False))
    

def matrice_correlation(tableau, titre):
    """Matrice de corrélation entre les variables numériques : la valeur est écrite dans chaque case."""
    ordre = list(NOMS_VARIABLES_COURTS.values())
    grille = tableau.pivot(index="variable_y", columns="variable_x", values="correlation")
    grille = grille.reindex(index=ordre, columns=ordre)
    fig = px.imshow(
        grille, text_auto=".2f", aspect="auto",
        color_continuous_scale=[[0, "#FC9935"], [0.5, "#F4F9E8"], [1, "#1F6B26"]], zmin=-1, zmax=1,
        labels={"x": "", "y": "", "color": "Corrélation"},
    )
    # échelle de couleur plus discrète : barre plus fine, titre à la taille du reste
    fig.update_coloraxes(colorbar=dict(thickness=14, len=0.8,title=dict(text="Corrélation", font=dict(size=13))))
    return _habiller(_finir(fig, legende=False))



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
    # l'axe horizontal a un titre : la marge et la légende descendent d'un cran
    return _habiller_origines(_finir(fig), bas=100, y_legende=-0.32)


def nuage_surface_conso(tableau, titre):
    """Un point par logement de l'échantillon : consommation selon la surface, couleur = étiquette DPE."""
    fig = px.scatter(
        tableau, x="surface_habitable_logement", y="conso_5_usages_par_m2_ef", color="etiquette_dpe",
        color_discrete_map=COULEURS, category_orders={"etiquette_dpe": ETIQUETTES}, opacity=0.7, title=titre,
        labels={"surface_habitable_logement": "Surface habitable (m²)",
                "conso_5_usages_par_m2_ef": "Consommation (kWh/m²/an)", "etiquette_dpe": "Étiquette"},
    )
    fig.update_traces(marker=dict(size=5))
    return _finir(fig)


def barres_departements(tableau, y, titre, libelle_y, format_texte=".0f"):
    """Une paire de barres (existants / neufs) par département."""
    # On retire les lignes « Tous » : on veut comparer les départements entre eux
    pas_tous = (tableau["departement"].astype(str) != "Tous") & (tableau["origine"].astype(str) != "Tous")
    tableau = tableau[pas_tous].copy()
    tableau["departement"] = tableau["departement"].astype(str).map(nom_departement)
    tableau["origine"] = tableau["origine"].astype(str).map(lambda code: NOMS_ORIGINES.get(code, code))
    fig = px.bar(
        tableau, x="departement", y=y, color="origine", barmode="group", text_auto=format_texte,
        color_discrete_map=COULEURS_ORIGINES, title=titre, labels={"departement": "", y: libelle_y},
    )
    # valeurs au-dessus des barres, coins arrondis, barres un peu plus espacées
    fig.update_traces(textposition="outside", cliponaxis=False,
                      textfont=dict(color="#17301B", size=13), marker_cornerradius=8)
    fig.update_layout(bargap=0.35, bargroupgap=0.08)
    return _habiller_origines(_finir(fig))


