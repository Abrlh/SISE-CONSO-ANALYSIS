"""
Tests unitaires des analyses (src/analysis.py).

On utilise un petit jeu de 8 logements dont on a calculé les résultats à la main,
pour vérifier que chaque tableau contient les bons chiffres.

Lancer : python -m pytest tests/test_analysis.py -v
"""
import pandas as pd
import pytest

from src.analysis import (
    ANALYSES,
    StatAnalyzer,
    conso_par_modalite,
    distribution_conso,
    etiquette_par_modalite,
    kpi_globaux,
    repartition_etiquettes,
    stats_conso,
)

COLONNES = ["origine", "etiquette_dpe", "conso_5_usages_par_m2_ep",
            "surface_habitable_logement", "periode_construction", "type_batiment",
            "type_energie_principale_chauffage", "qualite_isolation_enveloppe"]


def departement(code, lignes):
    df = pd.DataFrame(lignes, columns=COLONNES)
    df.insert(0, "code_departement_ban", code)
    df["colonne_ignoree"] = 1
    return df


def donnees():
    """8 logements. Résultats attendus (calculés à la main) :
    - conso : 400, 500, 200, 60 (dept 75) ; 150, 300, 40, 70 (dept 59)
    - médiane de tout : 175 ; moyenne : 215 ; passoires (F, G) : 2 sur 8 = 25 %
    """
    return {
        "75": departement("75", [
            ("dpe_existants", "F", 400, 30, "avant 1948", "appartement", "Gaz naturel", "insuffisante"),
            ("dpe_existants", "G", 500, 25, "avant 1948", "appartement", "Électricité", "insuffisante"),
            ("dpe_existants", "D", 200, 50, "1948-1974", "maison", "Gaz naturel", "moyenne"),
            ("dpe_neufs", "B", 60, 45, "après 2021", "appartement", "Électricité", "très bonne"),
        ]),
        "59": departement("59", [
            ("dpe_existants", "C", 150, 80, "1948-1974", "maison", None, "bonne"),
            ("dpe_existants", "E", 300, 70, "avant 1948", "maison", "Gaz naturel", "moyenne"),
            ("dpe_neufs", "A", 40, 90, "après 2021", "maison", "Électricité", "très bonne"),
            ("dpe_neufs", "B", 70, 60, "après 2021", "appartement", "Électricité", "très bonne"),
        ]),
    }


@pytest.fixture
def df():
    return pd.concat(donnees().values(), ignore_index=True)


def ligne(tableau, **criteres):
    """La seule ligne du tableau qui correspond aux critères (échoue s'il y en a 0 ou plusieurs)."""
    masque = pd.Series(True, index=tableau.index)
    for colonne, valeur in criteres.items():
        masque &= tableau[colonne] == valeur
    trouvees = tableau[masque]
    assert len(trouvees) == 1, f"{len(trouvees)} lignes pour {criteres}"
    return trouvees.iloc[0]


# ---------------------------------------------------------------------------
# kpi_globaux
# ---------------------------------------------------------------------------
def test_kpi_tous_les_logements(df):
    k = ligne(kpi_globaux(df), departement="Tous", origine="Tous")
    assert k["nb_logements"] == 8
    assert k["conso_mediane"] == pytest.approx(175.0)
    assert k["surface_mediane"] == pytest.approx(55.0)
    assert k["part_f_g"] == pytest.approx(25.0)
    assert k["part_a_b"] == pytest.approx(37.5)


def test_kpi_un_departement_et_une_origine(df):
    k = ligne(kpi_globaux(df), departement="75", origine="dpe_existants")
    assert k["nb_logements"] == 3
    assert k["conso_mediane"] == pytest.approx(400.0)
    assert k["part_f_g"] == pytest.approx(66.7)
    assert k["part_a_b"] == pytest.approx(0.0)


def test_kpi_contient_tous_les_perimetres(df):
    k = kpi_globaux(df)
    assert set(k["departement"]) == {"59", "75", "Tous"}
    assert set(k["origine"]) == {"dpe_existants", "dpe_neufs", "Tous"}
    assert len(k) == 9


def test_kpi_les_sous_totaux_s_additionnent(df):
    k = kpi_globaux(df)
    par_dept = k[(k["departement"] != "Tous") & (k["origine"] == "Tous")]["nb_logements"].sum()
    assert par_dept == ligne(k, departement="Tous", origine="Tous")["nb_logements"]


# ---------------------------------------------------------------------------
# repartition_etiquettes
# ---------------------------------------------------------------------------
def test_repartition_toujours_les_7_etiquettes(df):
    r = repartition_etiquettes(df)
    assert (r.groupby(["departement", "origine"]).size() == 7).all()
    assert ligne(r, departement="75", origine="dpe_neufs", etiquette="G")["effectif"] == 0


def test_repartition_chiffres(df):
    r = repartition_etiquettes(df)
    assert ligne(r, departement="Tous", origine="Tous", etiquette="B")["effectif"] == 2
    assert ligne(r, departement="Tous", origine="Tous", etiquette="B")["pourcentage"] == pytest.approx(25.0)
    assert ligne(r, departement="Tous", origine="Tous", etiquette="A")["pourcentage"] == pytest.approx(12.5)


def test_repartition_pourcentages_font_100(df):
    somme = repartition_etiquettes(df).groupby(["departement", "origine"])["pourcentage"].sum()
    assert (somme.round(1) == 100.0).all()


# ---------------------------------------------------------------------------
# distribution_conso
# ---------------------------------------------------------------------------
def test_histogramme_toutes_les_tranches_presentes(df):
    h = distribution_conso(df)
    assert (h.groupby(["departement", "origine"]).size() == 50).all()
    assert h["borne_min"].min() == 0 and h["borne_max"].max() == 1000


def test_histogramme_chiffres(df):
    h = distribution_conso(df)
    tous = h[(h["departement"] == "Tous") & (h["origine"] == "Tous")]
    assert tous["effectif"].sum() == 8
    # 60 et 70 kWh/m²/an tombent dans la tranche 60-80
    assert tous[tous["borne_min"] == 60]["effectif"].iloc[0] == 2
    assert tous[tous["borne_min"] == 40]["effectif"].iloc[0] == 1   # la valeur 40
    assert tous[tous["borne_min"] == 100]["effectif"].iloc[0] == 0


def test_histogramme_la_valeur_maximale_est_dans_la_derniere_tranche(df):
    df = df.copy()
    df.loc[0, "conso_5_usages_par_m2_ep"] = 1000      # le plafond du nettoyage
    h = distribution_conso(df)
    tous = h[(h["departement"] == "Tous") & (h["origine"] == "Tous")]
    assert tous[tous["borne_min"] == 980]["effectif"].iloc[0] == 1


# ---------------------------------------------------------------------------
# stats_conso
# ---------------------------------------------------------------------------
def test_stats_conso_chiffres(df):
    s = ligne(stats_conso(df), departement="Tous", origine="Tous")
    assert s["effectif"] == 8
    assert s["moyenne"] == pytest.approx(215.0)
    assert s["minimum"] == pytest.approx(40.0)
    assert s["maximum"] == pytest.approx(500.0)
    assert s["mediane"] == pytest.approx(175.0)


def test_stats_conso_les_percentiles_sont_ranges(df):
    s = ligne(stats_conso(df), departement="Tous", origine="Tous")
    assert s["minimum"] <= s["p05"] <= s["q1"] <= s["mediane"] <= s["q3"] <= s["p95"] <= s["maximum"]


# ---------------------------------------------------------------------------
# conso_par_modalite
# ---------------------------------------------------------------------------
def test_conso_par_modalite_chiffres(df):
    c = conso_par_modalite(df)
    gaz = ligne(c, variable="type_energie_principale_chauffage", modalite="Gaz naturel",
                departement="Tous", origine="Tous")
    assert gaz["effectif"] == 3
    assert gaz["mediane"] == pytest.approx(300.0)
    assert gaz["part_f_g"] == pytest.approx(33.3)


def test_conso_par_modalite_valeur_vide_devient_non_renseigne(df):
    c = conso_par_modalite(df)
    vide = ligne(c, variable="type_energie_principale_chauffage", modalite="(non renseigné)",
                 departement="Tous", origine="Tous")
    assert vide["effectif"] == 1


def test_conso_par_modalite_chaque_variable_couvre_tous_les_logements(df):
    c = conso_par_modalite(df)
    tous = c[(c["departement"] == "Tous") & (c["origine"] == "Tous")]
    assert (tous.groupby("variable")["effectif"].sum() == 8).all()


def test_conso_par_modalite_ordre_naturel_des_periodes(df):
    c = conso_par_modalite(df)
    p = c[(c["variable"] == "periode_construction") & (c["departement"] == "Tous") & (c["origine"] == "Tous")]
    ordre = dict(zip(p["modalite"], p["ordre"]))
    assert ordre["avant 1948"] < ordre["1948-1974"] < ordre["après 2021"]


def test_conso_par_modalite_ignore_une_variable_absente(df):
    c = conso_par_modalite(df.drop(columns="type_energie_principale_chauffage"))
    assert "type_energie_principale_chauffage" not in set(c["variable"])
    assert "type_batiment" in set(c["variable"])


# ---------------------------------------------------------------------------
# etiquette_par_modalite
# ---------------------------------------------------------------------------
def test_etiquette_par_modalite_chiffres(df):
    e = etiquette_par_modalite(df)
    maisons = e[(e["variable"] == "type_batiment") & (e["modalite"] == "maison")
                & (e["departement"] == "Tous") & (e["origine"] == "Tous")]
    # 4 maisons : D, C, E, A -> 25 % chacune
    assert maisons["effectif"].sum() == 4
    assert maisons["pourcentage"].sum() == pytest.approx(100.0)
    assert maisons[maisons["etiquette"] == "A"]["pourcentage"].iloc[0] == pytest.approx(25.0)
    assert maisons[maisons["etiquette"] == "F"]["pourcentage"].iloc[0] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# StatAnalyzer : l'ensemble
# ---------------------------------------------------------------------------
def test_compute_all_renvoie_toutes_les_analyses():
    analyzer = StatAnalyzer()
    resultats = analyzer.compute_all(donnees())
    assert set(resultats) == set(ANALYSES) == set(analyzer.noms())
    for nom, tableau in resultats.items():
        assert isinstance(tableau, pd.DataFrame) and len(tableau) > 0, nom


def test_compute_all_un_departement_sans_une_colonne_ne_plante_pas():
    data = donnees()
    data["59"] = data["59"].drop(columns="type_energie_principale_chauffage")
    c = StatAnalyzer().compute_all(data)["conso_par_modalite"]
    tous = c[(c["variable"] == "type_energie_principale_chauffage")
             & (c["departement"] == "Tous") & (c["origine"] == "Tous")]
    assert tous["effectif"].sum() == 8        # aucun logement perdu
    assert "(non renseigné)" in set(tous["modalite"])


def test_compute_all_ne_modifie_pas_les_donnees():
    data = donnees()
    copies = {k: v.copy(deep=True) for k, v in data.items()}
    StatAnalyzer().compute_all(data)
    for k in data:
        pd.testing.assert_frame_equal(data[k], copies[k])