"""
Analyses statistiques des DPE, pré-calculées pour l'application.

Principe : l'application Streamlit ne calcule rien, elle LIT. Ce module calcule une fois
(étape `--stats` de train.py) un ensemble de petits tableaux, enregistrés dans
data/stats/<snapshot>/<nom>.parquet par DataRepository.save_stats().

- Une analyse = une fonction qui reçoit UN DataFrame (tous les départements, déjà
  nettoyés) et renvoie UN petit DataFrame. Comme pour le nettoyage : une règle, une fonction.
- Chaque tableau contient les sous-totaux dont l'application a besoin : la valeur
  "Tous" dans `departement` ou `origine` veut dire "tous confondus". L'application
  filtre donc simplement (departement == "75", origine == "dpe_existants"...).
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
CONSO = "conso_5_usages_par_m2_ep"
SURFACE = "surface_habitable_logement"

TOUS = "Tous"                              # libellé des sous-totaux
NON_RENSEIGNE = "(non renseigné)"
ETIQUETTES = list("ABCDEFG")
PASSOIRES = ["F", "G"]                     # passoires thermiques
PAS_HISTOGRAMME = 20                       # kWh/m²/an par barre de l'histogramme

# Variables qualitatives analysées (celles qui n'existent pas dans les données sont ignorées)
VARIABLES_CATEGORIELLES = [
    "periode_construction", "type_batiment", "type_energie_principale_chauffage",
    "type_installation_chauffage", "type_installation_ecs",
    "qualite_isolation_enveloppe", "qualite_isolation_murs",
    "qualite_isolation_menuiseries", "qualite_isolation_plancher_bas",
]
# Variables dont les modalités ont un ordre naturel (pour l'affichage des graphiques)
ORDRES = {
    "periode_construction": ORDRE_PERIODE,
    "qualite_isolation_enveloppe": ORDRE_ISOLATION,
    "qualite_isolation_murs": ORDRE_ISOLATION,
    "qualite_isolation_menuiseries": ORDRE_ISOLATION,
    "qualite_isolation_plancher_bas": ORDRE_ISOLATION,
}

# Colonnes dont ce module a besoin (on n'en garde pas d'autres en mémoire)
COLONNES_UTILES = ([COL_DEPT_SOURCE, ORIGINE, ETIQUETTE, CONSO, SURFACE]
                   + VARIABLES_CATEGORIELLES)

QUANTILES = {0.05: "p05", 0.25: "q1", 0.5: "mediane", 0.75: "q3", 0.95: "p95"}


# ---------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------
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
    """Quartiles d'une colonne déjà groupée, en colonnes nommées."""
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
# Analyses : une fonction par tableau
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


def conso_par_modalite(df):
    """Consommation et part de passoires selon chaque variable qualitative (période de
    construction, énergie, isolation...). Une ligne par variable, modalité, département
    et origine : effectif, quartiles de la consommation, part de F et G, rang d'affichage."""
    variables = [v for v in VARIABLES_CATEGORIELLES if v in df.columns]
    base = _par_perimetre(_preparer(df, [COL_DEPT_SOURCE, ORIGINE, ETIQUETTE, CONSO] + variables))
    base["passoire"] = base[ETIQUETTE].isin(PASSOIRES)
    morceaux = []
    for v in variables:
        d = base[[DEPT, ORIGINE, CONSO, "passoire"]].assign(modalite=_modalite(base[v]))
        g = d.groupby([DEPT, ORIGINE, "modalite"])
        t = g.agg(effectif=(CONSO, "size"), part_f_g=("passoire", "mean"))
        t = t.join(_quantiles(g[CONSO])).reset_index()
        t["part_f_g"] = (100 * t["part_f_g"]).round(1)
        t[["q1", "mediane", "q3"]] = t[["q1", "mediane", "q3"]].round(1)
        t["ordre"] = _ordre_modalites(v, t)
        t.insert(0, "variable", v)
        morceaux.append(t)
    return pd.concat(morceaux, ignore_index=True)[
        ["variable", "modalite", "ordre", DEPT, ORIGINE, "effectif", "q1", "mediane", "q3", "part_f_g"]]


def etiquette_par_modalite(df):
    """Répartition des étiquettes A à G à l'intérieur de chaque modalité (ex. quelle part
    de A à G parmi les logements chauffés au gaz ?). Pourcentages calculés par modalité."""
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
}


class StatAnalyzer():
    """Calcule toutes les analyses à partir des données propres."""

    def __init__(self):
        pass

    def noms(self)-> list[str]:
        """Noms des analyses disponibles."""
        return list(ANALYSES)

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
        resultats = {}
        for nom, analyse in ANALYSES.items():
            print(f"    - {nom}")
            resultats[nom] = analyse(df)
        return resultats