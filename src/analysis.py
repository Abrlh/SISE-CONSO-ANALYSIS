"""
Analyses statistiques des DPE, pré-calculées pour l'application.

Principe : l'application Streamlit ne calcule rien, elle LIT. Ce module calcule une fois
(étape `--stats` de train.py) un ensemble de petits tableaux, enregistrés dans
data/stats/<snapshot>/<nom>.parquet par DataRepository.save_stats().

- Une analyse = une fonction qui reçoit UN DataFrame (tous les départements, déjà
  nettoyés) et renvoie UN petit DataFrame. Comme pour le nettoyage : une règle, une fonction.
  Seule exception : qualite_donnees(), qui a besoin des colonnes complètes de chaque
  département ({departement: DataFrame}).
- Chaque tableau contient les sous-totaux dont l'application a besoin : la valeur
  "Tous" dans `departement` ou `origine` veut dire "tous confondus". L'application
  filtre donc simplement (departement == "75", origine == "dpe_existants"...).
- Si une colonne nécessaire manque dans les données, l'analyse renvoie un tableau vide
  (mêmes colonnes) au lieu de planter : un rafraîchissement ne casse pas l'application.
- Pour ajouter une analyse : écrire la fonction, puis l'ajouter au dictionnaire ANALYSES
  en bas du fichier. Elle sera calculée et enregistrée automatiquement.
"""
import numpy as np
import pandas as pd

from .preprocessing import CONSO_MAX, ORDRE_ISOLATION, ORDRE_PERIODE

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
COL_DEPT_SOURCE = "code_departement_ban"   # nom dans les données propres
DEPT = "departement"                       # nom dans les tableaux de statistiques
ORIGINE = "origine"
ETIQUETTE = "etiquette_dpe"
ETIQUETTE_GES = "etiquette_ges"
CONSO = "conso_5_usages_par_m2_ep"
SURFACE = "surface_habitable_logement"
HAUTEUR = "hauteur_sous_plafond"
GES = "emission_ges_5_usages_par_m2"
COUT = "cout_total_5_usages"
ENERGIE = "type_energie_principale_chauffage"
DATE = "date_reception_dpe"
COMMUNE = "nom_commune_ban"
INSEE = "code_insee_ban"
LAT, LON = "latitude", "longitude"

TOUS = "Tous"                              # libellé des sous-totaux
NON_RENSEIGNE = "(non renseigné)"
ETIQUETTES = list("ABCDEFG")
PASSOIRES = ["F", "G"]                     # passoires thermiques
PAS_HISTOGRAMME = 20                       # kWh/m²/an par barre de l'histogramme
MIN_LOGEMENTS_COMMUNE = 30                 # une commune plus petite n'est pas affichée
POINTS_PAR_DEPARTEMENT = 2000              # taille de l'échantillon (carte, nuage de points)

# Colonnes créées par ce module à partir des données propres (voir _enrichir)
ORDRE_SURFACE = ["moins de 20 m²", "20-30 m²", "30-40 m²", "40-60 m²", "60-80 m²",
                 "80-100 m²", "100-150 m²", "150 m² et plus"]
BORNES_SURFACE = [0, 20, 30, 40, 60, 80, 100, 150, np.inf]
ORDRE_ENERGIE = ["Électricité", "Gaz naturel", "Réseau de chaleur", "Fioul", "Bois", "Autre"]

# Variables qualitatives analysées (celles qui n'existent pas dans les données sont ignorées)
VARIABLES_CATEGORIELLES = [
    "periode_construction", "type_batiment", ENERGIE,
    "type_installation_chauffage", "type_installation_ecs",
    "qualite_isolation_enveloppe", "qualite_isolation_murs",
    "qualite_isolation_menuiseries", "qualite_isolation_plancher_bas",
    "famille_energie", "tranche_surface",      # créées par _enrichir()
]
# Variables dont les modalités ont un ordre naturel (pour l'affichage des graphiques)
ORDRES = {
    "famille_energie": ORDRE_ENERGIE,
    "tranche_surface": ORDRE_SURFACE,
    "periode_construction": ORDRE_PERIODE,
    "qualite_isolation_enveloppe": ORDRE_ISOLATION,
    "qualite_isolation_murs": ORDRE_ISOLATION,
    "qualite_isolation_menuiseries": ORDRE_ISOLATION,
    "qualite_isolation_plancher_bas": ORDRE_ISOLATION,
}

# Colonnes dont ce module a besoin (on n'en garde pas d'autres en mémoire)
COLONNES_UTILES = list(dict.fromkeys(
    [COL_DEPT_SOURCE, ORIGINE, ETIQUETTE, ETIQUETTE_GES, CONSO, SURFACE, HAUTEUR, GES, COUT,
     ENERGIE, DATE, COMMUNE, INSEE, LAT, LON]
    + [v for v in VARIABLES_CATEGORIELLES if v not in ("famille_energie", "tranche_surface")]))

# Colonnes numériques dont on calcule les corrélations
COLONNES_CORRELATION = [CONSO, SURFACE, HAUTEUR, GES, COUT]

# Colonnes de la table légère de logements (filtres, nuage de points, export CSV)
COLONNES_LOGEMENTS = [
    COL_DEPT_SOURCE, ORIGINE, ETIQUETTE, CONSO, SURFACE, "periode_construction", "type_batiment",
    ENERGIE, "famille_energie", "tranche_surface", "qualite_isolation_enveloppe",
    "annee_reception", INSEE, COMMUNE, LAT, LON,
]

QUANTILES = {0.05: "p05", 0.25: "q1", 0.5: "mediane", 0.75: "q3", 0.95: "p95"}


# ---------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------
def _famille_energie(serie):
    """Regroupe les énergies de chauffage en 6 familles (le bois a plusieurs variantes,
    l'électricité aussi). Les cases vides restent vides."""
    t = serie.astype("string").str.lower()
    conditions = [
        t.str.startswith("électricité", na=False).to_numpy(dtype=bool),
        t.str.startswith("gaz", na=False).to_numpy(dtype=bool),
        t.str.contains("réseau", na=False).to_numpy(dtype=bool),
        t.str.startswith("fioul", na=False).to_numpy(dtype=bool),
        t.str.contains("bois", na=False).to_numpy(dtype=bool),
    ]
    choix = ["Électricité", "Gaz naturel", "Réseau de chaleur", "Fioul", "Bois"]
    famille = pd.Series(np.select(conditions, choix, default="Autre"), index=serie.index)
    return famille.where(serie.notna())


def _enrichir(df):
    """Ajoute, si elles n'existent pas encore et si la colonne source est présente :
    famille_energie, tranche_surface et annee_reception. Ne copie rien s'il n'y a rien à ajouter."""
    a_faire = []
    if ENERGIE in df.columns and "famille_energie" not in df.columns:
        a_faire.append("famille_energie")
    if SURFACE in df.columns and "tranche_surface" not in df.columns:
        a_faire.append("tranche_surface")
    if DATE in df.columns and "annee_reception" not in df.columns:
        a_faire.append("annee_reception")
    if not a_faire:
        return df
    df = df.copy()
    if "famille_energie" in a_faire:
        df["famille_energie"] = _famille_energie(df[ENERGIE])
    if "tranche_surface" in a_faire:
        df["tranche_surface"] = pd.cut(df[SURFACE], bins=BORNES_SURFACE, labels=ORDRE_SURFACE,
                                       right=False).astype("object")
    if "annee_reception" in a_faire:
        df["annee_reception"] = pd.to_datetime(df[DATE], errors="coerce").dt.year
    return df


def _vide(colonnes):
    """Tableau vide avec les bonnes colonnes (quand les données nécessaires manquent)."""
    return pd.DataFrame({c: pd.Series(dtype="object") for c in colonnes})


def _manque(df, *colonnes):
    return any(c not in df.columns for c in colonnes)


def _preparer(df, colonnes):
    """Garde les colonnes demandées (si elles existent) et renomme le département."""
    colonnes = [c for c in colonnes if c in df.columns]
    out = df[colonnes].copy()
    out = out.rename(columns={COL_DEPT_SOURCE: DEPT})
    for c in (DEPT, ORIGINE):
        out[c] = out[c].astype(str)
    return out


def _avec_total(df, colonne):
    """Ajoute une copie de df où `colonne` vaut "Tous" : un groupby donne alors aussi le
    sous-total (tous départements, toutes origines...) sans calcul supplémentaire."""
    return pd.concat([df, df.assign(**{colonne: TOUS})], ignore_index=True)


def _par_perimetre(df):
    """Duplique les lignes pour obtenir tous les périmètres : chaque département et
    "Tous", croisés avec chaque origine et "Tous"."""
    return _avec_total(_avec_total(df, DEPT), ORIGINE)


def _quantiles(groupe, noms=("q1", "mediane", "q3")):
    """Quantiles d'une colonne déjà groupée, en colonnes nommées."""
    niveaux = [q for q, nom in QUANTILES.items() if nom in noms]
    q = groupe.quantile(niveaux).unstack()
    return q.rename(columns=QUANTILES)


def _ordre_modalites(variable, t):
    """Rang d'affichage de chaque modalité : l'ordre naturel s'il existe (périodes,
    isolation), sinon de la plus fréquente à la moins fréquente. `t` doit contenir
    departement, origine, modalite et effectif."""
    tous = t[(t[DEPT] == TOUS) & (t[ORIGINE] == TOUS)]
    frequence = tous.groupby("modalite")["effectif"].sum().sort_values(ascending=False)
    if variable in ORDRES:
        rang = {m: i for i, m in enumerate(ORDRES[variable])}
        for m in frequence.index:           # valeurs hors liste (dont "non renseigné") à la fin
            if m not in rang:
                rang[m] = len(rang)
    else:
        rang = {m: i for i, m in enumerate(frequence.index)}
    return t["modalite"].map(rang)


def _modalite(serie):
    """Valeurs de la variable en texte, "(non renseigné)" pour les cases vides."""
    return serie.astype("object").where(serie.notna(), NON_RENSEIGNE).astype(str)


# ---------------------------------------------------------------------------
# Analyses de base : chiffres clés, étiquettes, consommation
# ---------------------------------------------------------------------------
def kpi_globaux(df):
    """Chiffres clés par département et par origine (+ "Tous") : nombre de logements,
    consommation et surface médianes, part de passoires thermiques (F et G) et de A et B."""
    d = _par_perimetre(_preparer(df, [COL_DEPT_SOURCE, ORIGINE, ETIQUETTE, CONSO, SURFACE]))
    d["passoire"] = d[ETIQUETTE].isin(PASSOIRES)
    d["a_ou_b"] = d[ETIQUETTE].isin(["A", "B"])
    out = d.groupby([DEPT, ORIGINE]).agg(
        nb_logements=(CONSO, "size"),
        conso_mediane=(CONSO, "median"),
        surface_mediane=(SURFACE, "median"),
        part_f_g=("passoire", "mean"),
        part_a_b=("a_ou_b", "mean"),
    ).reset_index()
    out["part_f_g"] = (100 * out["part_f_g"]).round(1)
    out["part_a_b"] = (100 * out["part_a_b"]).round(1)
    out[["conso_mediane", "surface_mediane"]] = out[["conso_mediane", "surface_mediane"]].round(1)
    return out


def repartition_etiquettes(df):
    """Nombre et pourcentage de logements par étiquette A à G, pour chaque département
    et chaque origine (+ "Tous"). Les 7 étiquettes sont toujours présentes (effectif 0 si besoin)."""
    d = _par_perimetre(_preparer(df, [COL_DEPT_SOURCE, ORIGINE, ETIQUETTE]))
    cube = (d.groupby([DEPT, ORIGINE, ETIQUETTE]).size()
              .unstack(ETIQUETTE, fill_value=0)
              .reindex(columns=ETIQUETTES, fill_value=0))
    out = cube.reset_index().melt(id_vars=[DEPT, ORIGINE], var_name="etiquette", value_name="effectif")
    total = out.groupby([DEPT, ORIGINE])["effectif"].transform("sum")
    out["pourcentage"] = (100 * out["effectif"] / total).round(2)
    return out.sort_values([DEPT, ORIGINE, "etiquette"], ignore_index=True)


def distribution_conso(df):
    """Histogramme de la consommation (kWh/m²/an) par tranches de 20, pour chaque
    département et origine (+ "Tous"). Toutes les tranches sont présentes."""
    nb_tranches = int(np.ceil(CONSO_MAX / PAS_HISTOGRAMME))
    d = _par_perimetre(_preparer(df, [COL_DEPT_SOURCE, ORIGINE, CONSO]))
    d["tranche"] = np.minimum((d[CONSO] // PAS_HISTOGRAMME).astype(int), nb_tranches - 1)
    grille = pd.MultiIndex.from_product(
        [sorted(d[DEPT].unique()), sorted(d[ORIGINE].unique()), range(nb_tranches)],
        names=[DEPT, ORIGINE, "tranche"])
    out = (d.groupby([DEPT, ORIGINE, "tranche"]).size()
             .reindex(grille, fill_value=0).rename("effectif").reset_index())
    out["borne_min"] = out["tranche"] * PAS_HISTOGRAMME
    out["borne_max"] = out["borne_min"] + PAS_HISTOGRAMME
    total = out.groupby([DEPT, ORIGINE])["effectif"].transform("sum")
    out["pourcentage"] = (100 * out["effectif"] / total.where(total > 0)).round(2)
    return out.drop(columns="tranche")[[DEPT, ORIGINE, "borne_min", "borne_max", "effectif", "pourcentage"]]


def stats_conso(df):
    """Statistiques descriptives de la consommation par département et origine (+ "Tous") :
    effectif, moyenne, écart-type, minimum, percentiles 5/25/50/75/95, maximum."""
    d = _par_perimetre(_preparer(df, [COL_DEPT_SOURCE, ORIGINE, CONSO]))
    g = d.groupby([DEPT, ORIGINE])[CONSO]
    base = g.agg(effectif="size", moyenne="mean", ecart_type="std", minimum="min", maximum="max")
    out = base.join(_quantiles(g, noms=QUANTILES.values())).reset_index()
    colonnes = [DEPT, ORIGINE, "effectif", "moyenne", "ecart_type", "minimum",
                "p05", "q1", "mediane", "q3", "p95", "maximum"]
    out[colonnes[3:]] = out[colonnes[3:]].round(1)
    return out[colonnes]


# ---------------------------------------------------------------------------
# Consommation et étiquettes selon les caractéristiques du logement
# ---------------------------------------------------------------------------
def conso_par_modalite(df):
    """Consommation et part de passoires selon chaque variable qualitative (période de
    construction, énergie, isolation, tranche de surface...). Une ligne par variable,
    modalité, département et origine : effectif, p5/quartiles/p95 de la consommation
    (de quoi tracer une boîte à moustaches), part de F et G, rang d'affichage."""
    df = _enrichir(df)
    variables = [v for v in VARIABLES_CATEGORIELLES if v in df.columns]
    base = _par_perimetre(_preparer(df, [COL_DEPT_SOURCE, ORIGINE, ETIQUETTE, CONSO] + variables))
    base["passoire"] = base[ETIQUETTE].isin(PASSOIRES)
    noms_q = ("p05", "q1", "mediane", "q3", "p95")
    morceaux = []
    for v in variables:
        d = base[[DEPT, ORIGINE, CONSO, "passoire"]].assign(modalite=_modalite(base[v]))
        g = d.groupby([DEPT, ORIGINE, "modalite"])
        t = g.agg(effectif=(CONSO, "size"), part_f_g=("passoire", "mean"))
        t = t.join(_quantiles(g[CONSO], noms=noms_q)).reset_index()
        t["part_f_g"] = (100 * t["part_f_g"]).round(1)
        t[list(noms_q)] = t[list(noms_q)].round(1)
        t["ordre"] = _ordre_modalites(v, t)
        t.insert(0, "variable", v)
        morceaux.append(t)
    return pd.concat(morceaux, ignore_index=True)[
        ["variable", "modalite", "ordre", DEPT, ORIGINE, "effectif",
         "p05", "q1", "mediane", "q3", "p95", "part_f_g"]]


def etiquette_par_modalite(df):
    """Répartition des étiquettes A à G à l'intérieur de chaque modalité (ex. quelle part
    de A à G parmi les logements chauffés au gaz ?). Pourcentages calculés par modalité."""
    df = _enrichir(df)
    variables = [v for v in VARIABLES_CATEGORIELLES if v in df.columns]
    base = _par_perimetre(_preparer(df, [COL_DEPT_SOURCE, ORIGINE, ETIQUETTE] + variables))
    morceaux = []
    for v in variables:
        d = base[[DEPT, ORIGINE, ETIQUETTE]].assign(modalite=_modalite(base[v]))
        cube = (d.groupby([DEPT, ORIGINE, "modalite", ETIQUETTE]).size()
                  .unstack(ETIQUETTE, fill_value=0)
                  .reindex(columns=ETIQUETTES, fill_value=0))
        t = cube.reset_index().melt(id_vars=[DEPT, ORIGINE, "modalite"],
                                    var_name="etiquette", value_name="effectif")
        total = t.groupby([DEPT, ORIGINE, "modalite"])["effectif"].transform("sum")
        t["pourcentage"] = (100 * t["effectif"] / total).round(2)
        t["ordre"] = _ordre_modalites(v, t)
        t.insert(0, "variable", v)
        morceaux.append(t)
    return pd.concat(morceaux, ignore_index=True)[
        ["variable", "modalite", "ordre", DEPT, ORIGINE, "etiquette", "effectif", "pourcentage"]]


def conso_par_etiquette(df):
    """Consommation de chaque étiquette A à G, selon la famille d'énergie de chauffage
    (+ "Tous"), par département et origine : c'est la question du client (impact de la
    classe DPE sur la consommation, notamment électrique). Effectif, moyenne, quartiles."""
    df = _enrichir(df)
    if "famille_energie" not in df.columns:
        df = df.assign(famille_energie=NON_RENSEIGNE)
    base = _par_perimetre(_preparer(df, [COL_DEPT_SOURCE, ORIGINE, ETIQUETTE, CONSO, "famille_energie"]))
    base["famille_energie"] = _modalite(base["famille_energie"])
    base = _avec_total(base, "famille_energie")
    g = base.groupby([DEPT, ORIGINE, "famille_energie", ETIQUETTE])[CONSO]
    t = g.agg(effectif="size", moyenne="mean").join(_quantiles(g)).reset_index()
    t = t.rename(columns={ETIQUETTE: "etiquette"})
    t[["moyenne", "q1", "mediane", "q3"]] = t[["moyenne", "q1", "mediane", "q3"]].round(1)
    return t[[DEPT, ORIGINE, "famille_energie", "etiquette", "effectif", "moyenne", "q1", "mediane", "q3"]]


def cout_ges_par_etiquette(df):
    """Pour chaque étiquette : consommation médiane, coût médian par m² (cout_total_5_usages
    divisé par la surface, dans l'unité de la source) et émissions de gaz à effet de serre
    médianes (kg CO2/m²/an)."""
    colonnes = [DEPT, ORIGINE, "etiquette", "effectif", "conso_mediane", "cout_par_m2_median", "ges_median"]
    if _manque(df, COUT, GES, SURFACE):
        return _vide(colonnes)
    d = _par_perimetre(_preparer(df, [COL_DEPT_SOURCE, ORIGINE, ETIQUETTE, CONSO, SURFACE, COUT, GES]))
    d["cout_par_m2"] = d[COUT] / d[SURFACE]
    out = d.groupby([DEPT, ORIGINE, ETIQUETTE]).agg(
        effectif=(CONSO, "size"), conso_mediane=(CONSO, "median"),
        cout_par_m2_median=("cout_par_m2", "median"), ges_median=(GES, "median"),
    ).reset_index().rename(columns={ETIQUETTE: "etiquette"})
    out[["conso_mediane", "cout_par_m2_median", "ges_median"]] = \
        out[["conso_mediane", "cout_par_m2_median", "ges_median"]].round(2)
    return out[colonnes]


def etiquette_ges_vs_dpe(df):
    """Croisement étiquette DPE (consommation) contre étiquette GES (émissions), par origine
    (+ "Tous") : pour chaque étiquette DPE, répartition des étiquettes GES. Grille complète 7x7."""
    colonnes = [ORIGINE, "etiquette_dpe", "etiquette_ges", "effectif", "pourcentage"]
    if _manque(df, ETIQUETTE_GES):
        return _vide(colonnes)
    d = _avec_total(_preparer(df, [COL_DEPT_SOURCE, ORIGINE, ETIQUETTE, ETIQUETTE_GES]), ORIGINE)
    d = d[d[ETIQUETTE_GES].isin(ETIQUETTES)]
    cube = d.groupby([ORIGINE, ETIQUETTE, ETIQUETTE_GES]).size().unstack(ETIQUETTE_GES, fill_value=0)
    cube = cube.reindex(columns=ETIQUETTES, fill_value=0)
    grille = pd.MultiIndex.from_product([sorted(d[ORIGINE].unique()), ETIQUETTES], names=[ORIGINE, ETIQUETTE])
    cube = cube.reindex(grille, fill_value=0)
    out = cube.reset_index().melt(id_vars=[ORIGINE, ETIQUETTE], var_name="etiquette_ges", value_name="effectif")
    out = out.rename(columns={ETIQUETTE: "etiquette_dpe"})
    total = out.groupby([ORIGINE, "etiquette_dpe"])["effectif"].transform("sum")
    out["pourcentage"] = (100 * out["effectif"] / total.where(total > 0)).round(2)
    return out.sort_values([ORIGINE, "etiquette_dpe", "etiquette_ges"], ignore_index=True)[colonnes]


def correlations(df):
    """Corrélations de Spearman entre variables numériques (consommation, surface, hauteur,
    émissions, coût), par origine (+ "Tous"). Format long : variable_x, variable_y, correlation.
    Attention : émissions et coût contiennent la réponse, à ne pas utiliser comme entrées d'un modèle."""
    colonnes = [ORIGINE, "variable_x", "variable_y", "correlation"]
    cols = [c for c in COLONNES_CORRELATION if c in df.columns]
    if len(cols) < 2:
        return _vide(colonnes)
    d = _avec_total(_preparer(df, [COL_DEPT_SOURCE, ORIGINE] + cols), ORIGINE)
    morceaux = []
    for origine, sous in d.groupby(ORIGINE):
        m = sous[cols].corr(method="spearman")
        m.index.name = "variable_x"
        t = m.reset_index().melt(id_vars="variable_x", var_name="variable_y", value_name="correlation")
        t.insert(0, ORIGINE, origine)
        morceaux.append(t)
    out = pd.concat(morceaux, ignore_index=True)
    out["correlation"] = out["correlation"].round(3)
    return out[colonnes]


# ---------------------------------------------------------------------------
# Temps, géographie, qualité des données
# ---------------------------------------------------------------------------
def evolution_annuelle(df):
    """Nombre de logements, consommation médiane et part de passoires par année de réception
    du DPE, par département et origine (+ "Tous"). Attention : l'échantillon n'est pas
    forcément tiré au hasard dans le temps, ne pas conclure sur une tendance réelle."""
    colonnes = [DEPT, ORIGINE, "annee", "effectif", "conso_mediane", "part_f_g"]
    df = _enrichir(df)
    if "annee_reception" not in df.columns:
        return _vide(colonnes)
    d = _preparer(df, [COL_DEPT_SOURCE, ORIGINE, ETIQUETTE, CONSO, "annee_reception"])
    d = d.dropna(subset=["annee_reception"])
    d["annee_reception"] = d["annee_reception"].astype(int)
    d = _par_perimetre(d)
    d["passoire"] = d[ETIQUETTE].isin(PASSOIRES)
    out = d.groupby([DEPT, ORIGINE, "annee_reception"]).agg(
        effectif=(CONSO, "size"), conso_mediane=(CONSO, "median"), part_f_g=("passoire", "mean"),
    ).reset_index().rename(columns={"annee_reception": "annee"})
    out["conso_mediane"] = out["conso_mediane"].round(1)
    out["part_f_g"] = (100 * out["part_f_g"]).round(1)
    return out[colonnes]


def couverture_temporelle(df):
    """Dates de réception du premier et du dernier DPE, et nombre de logements, par
    département et origine (+ "Tous"). Sert à la page Contexte et à savoir jusqu'où va le snapshot."""
    colonnes = [DEPT, ORIGINE, "nb_logements", "date_min", "date_max"]
    if _manque(df, DATE):
        return _vide(colonnes)
    d = _preparer(df, [COL_DEPT_SOURCE, ORIGINE, DATE])
    d[DATE] = pd.to_datetime(d[DATE], errors="coerce")
    d = _par_perimetre(d.dropna(subset=[DATE]))
    out = d.groupby([DEPT, ORIGINE])[DATE].agg(
        nb_logements="size", date_min="min", date_max="max").reset_index()
    return out[colonnes]


def communes(df):
    """Une ligne par commune (et origine, + "Tous") : nombre de logements, consommation
    médiane, part de passoires, position (médiane des coordonnées). Les communes de moins de
    MIN_LOGEMENTS_COMMUNE logements ne sont pas gardées. Sert à la carte."""
    colonnes = [DEPT, "code_insee", "commune", ORIGINE, "effectif", "conso_mediane",
                "part_f_g", "latitude", "longitude"]
    if _manque(df, INSEE, COMMUNE, LAT, LON):
        return _vide(colonnes)
    d = _avec_total(_preparer(df, [COL_DEPT_SOURCE, ORIGINE, ETIQUETTE, CONSO, INSEE, COMMUNE, LAT, LON]), ORIGINE)
    d["passoire"] = d[ETIQUETTE].isin(PASSOIRES)
    out = d.groupby([DEPT, INSEE, ORIGINE]).agg(
        commune=(COMMUNE, "first"), effectif=(CONSO, "size"), conso_mediane=(CONSO, "median"),
        part_f_g=("passoire", "mean"), latitude=(LAT, "median"), longitude=(LON, "median"),
    ).reset_index().rename(columns={INSEE: "code_insee"})
    out = out[out["effectif"] >= MIN_LOGEMENTS_COMMUNE].reset_index(drop=True)
    out["conso_mediane"] = out["conso_mediane"].round(1)
    out["part_f_g"] = (100 * out["part_f_g"]).round(1)
    out[["latitude", "longitude"]] = out[["latitude", "longitude"]].round(5)
    return out[colonnes]


def echantillon_points(df):
    """Échantillon aléatoire (POINTS_PAR_DEPARTEMENT par département, toujours le même grâce
    à une graine fixe) de logements avec leur position : pour les markers de la carte et
    le nuage de points (surface contre consommation)."""
    colonnes = [DEPT, ORIGINE, ETIQUETTE, CONSO, SURFACE, LAT, LON, COMMUNE,
                "periode_construction", "type_batiment", "famille_energie"]
    df = _enrichir(df)
    if _manque(df, LAT, LON):
        return _vide(colonnes)
    d = _preparer(df, [COL_DEPT_SOURCE] + colonnes[1:]).dropna(subset=[LAT, LON])
    morceaux = [g.sample(n=min(len(g), POINTS_PAR_DEPARTEMENT), random_state=0)
                for _, g in d.groupby(DEPT)]
    if not morceaux:
        return _vide(colonnes)
    return pd.concat(morceaux, ignore_index=True)


def table_logements(df):
    """Table légère : une ligne par logement, une quinzaine de colonnes. L'application la
    charge une fois en mémoire pour les filtres (sliders, listes) et l'export CSV des
    données sélectionnées. Les textes sont en 'category' pour économiser la mémoire."""
    df = _enrichir(df)
    out = _preparer(df, COLONNES_LOGEMENTS)
    if "annee_reception" in out.columns:
        out["annee_reception"] = out["annee_reception"].astype("Int16")
    for c in out.columns:
        if pd.api.types.is_float_dtype(out[c]) and out[c].dtype != "float32":
            out[c] = out[c].astype("float32")
        elif not pd.api.types.is_numeric_dtype(out[c]):
            out[c] = out[c].astype("category")
    return out


def qualite_donnees(data):
    """Taux de cases vides de chaque colonne, par département (+ "Tous") : pour la page
    Contexte. Prend {departement: DataFrame} (colonnes complètes). Une colonne retirée du
    département par le nettoyage (trop vide) a presente=False et compte comme 100 % vide."""
    lignes = pd.Series({d: len(df) for d, df in data.items()})
    manquants = pd.DataFrame({d: df.isna().sum() for d, df in data.items()})
    presente = manquants.notna()
    manquants = manquants.fillna(lignes)             # colonne absente = tout manquant
    types = {}
    for df in data.values():
        for c in df.columns:
            types.setdefault(c, str(df[c].dtype))
    pct = (100 * manquants / lignes).round(2)
    pct[TOUS] = (100 * manquants.sum(axis=1) / lignes.sum()).round(2)
    presente[TOUS] = presente.any(axis=1)
    out = pct.reset_index(names="colonne").melt(
        id_vars="colonne", var_name=DEPT, value_name="pct_manquant")
    pres = presente.reset_index(names="colonne").melt(
        id_vars="colonne", var_name=DEPT, value_name="presente")
    out = out.merge(pres, on=["colonne", DEPT])
    out["type"] = out["colonne"].map(types)
    return out[[DEPT, "colonne", "type", "pct_manquant", "presente"]].sort_values(
        [DEPT, "pct_manquant", "colonne"], ascending=[True, False, True], ignore_index=True)


# ---------------------------------------------------------------------------
# Liste des analyses calculées par `train.py --stats`
# ---------------------------------------------------------------------------
ANALYSES = {
    "kpi_globaux": kpi_globaux,
    "repartition_etiquettes": repartition_etiquettes,
    "distribution_conso": distribution_conso,
    "stats_conso": stats_conso,
    "conso_par_modalite": conso_par_modalite,
    "etiquette_par_modalite": etiquette_par_modalite,
    "conso_par_etiquette": conso_par_etiquette,
    "cout_ges_par_etiquette": cout_ges_par_etiquette,
    "etiquette_ges_vs_dpe": etiquette_ges_vs_dpe,
    "correlations": correlations,
    "evolution_annuelle": evolution_annuelle,
    "couverture_temporelle": couverture_temporelle,
    "communes": communes,
    "echantillon_points": echantillon_points,
    "logements": table_logements,
}


class StatAnalyzer():
    """Calcule toutes les analyses à partir des données propres."""

    def __init__(self):
        pass

    def noms(self)-> list[str]:
        """Noms de toutes les analyses calculées par compute_all()."""
        return list(ANALYSES) + ["qualite_donnees"]

    def compute_all(self, data:dict[str, pd.DataFrame])-> dict[str, pd.DataFrame]:
        """Calcule toutes les analyses.

        Args:
            data: {departement: DataFrame propre}, tel que renvoyé par
                  DataRepository.load_processed()

        Returns:
            {nom_analyse: DataFrame}, prêt pour DataRepository.save_stats()
        """
        # On ne garde que les colonnes utiles : inutile de charger les ~160 colonnes
        df = pd.concat(
            [d[[c for c in COLONNES_UTILES if c in d.columns]] for d in data.values()],
            ignore_index=True)
        df = _enrichir(df)
        resultats = {}
        for nom, analyse in ANALYSES.items():
            print(f"    - {nom}")
            resultats[nom] = analyse(df)
        print("    - qualite_donnees")
        resultats["qualite_donnees"] = qualite_donnees(data)
        return resultats