"""
Tests unitaires des analyses (src/processing/analysis.py).

On utilise un petit jeu de 8 logements dont on a calculé les résultats à la main,
pour vérifier que chaque tableau contient les bons chiffres.

Lancer : python -m pytest tests/test_analysis.py -v
"""
from unittest.mock import patch

import pandas as pd
import pytest

from src.processing import analysis
from src.processing.analysis import (
    ANALYSES,
    StatAnalyzer,
    _famille_energie,
    apercu_donnees,
    bilan_nettoyage,
    colonnes_retirees,
    communes,
    conso_par_etiquette,
    conso_par_modalite,
    correlations,
    cout_ges_par_etiquette,
    couverture_temporelle,
    distribution_conso,
    echantillon_points,
    etiquette_ges_vs_dpe,
    etiquette_par_modalite,
    evolution_annuelle,
    kpi_globaux,
    qualite_donnees,
    repartition_etiquettes,
    stats_conso,
    stats_numeriques,
    table_logements,
)

COLONNES = [
    "origine", "etiquette_dpe", "conso_5_usages_par_m2_ep", "surface_habitable_logement",
    "periode_construction", "type_batiment", "type_energie_principale_chauffage",
    "qualite_isolation_enveloppe", "date_reception_dpe", "latitude", "longitude",
    "nom_commune_ban", "code_insee_ban", "etiquette_ges", "cout_total_5_usages",
    "emission_ges_5_usages_par_m2", "hauteur_sous_plafond",
]


def departement(code, lignes):
    df = pd.DataFrame(lignes, columns=COLONNES)
    df.insert(0, "code_departement_ban", code)
    df["date_reception_dpe"] = pd.to_datetime(df["date_reception_dpe"])
    return df


def donnees():
    """8 logements. Résultats attendus (calculés à la main) :
    - conso : 400, 500, 200, 60 (dept 75) ; 150, 300, 40, 70 (dept 59)
    - médiane de tout : 175 ; moyenne : 215 ; passoires (F, G) : 2 sur 8 = 25 %
    - le coût et les émissions augmentent avec la consommation
    """
    return {
        "75": departement("75", [
            ("dpe_existants", "F", 400, 30, "avant 1948", "appartement", "Gaz naturel", "insuffisante",
             "2021-03-01", 48.85, 2.35, "Paris 1er", "75101", "F", 1200, 80, 2.5),
            ("dpe_existants", "G", 500, 25, "avant 1948", "appartement", "Électricité", "insuffisante",
             "2021-06-01", 48.86, 2.36, "Paris 1er", "75101", "G", 2000, 90, 2.5),
            ("dpe_existants", "D", 200, 50, "1948-1974", "maison", "Gaz naturel", "moyenne",
             "2022-01-10", 48.87, 2.37, "Paris 1er", "75101", "D", 900, 30, 2.5),
            ("dpe_neufs", "B", 60, 45, "après 2021", "appartement", "Électricité", "très bonne",
             "2023-05-05", 48.88, 2.38, "Paris 2e", "75102", "A", 300, 5, 2.5),
        ]),
        "59": departement("59", [
            ("dpe_existants", "C", 150, 80, "1948-1974", "maison", None, "bonne",
             "2022-02-02", 50.63, 3.06, "Lille", "59350", "C", 800, 20, 2.5),
            ("dpe_existants", "E", 300, 70, "avant 1948", "maison", "Gaz naturel", "moyenne",
             "2022-07-07", 50.64, 3.07, "Lille", "59350", "E", 1100, 50, 2.5),
            ("dpe_neufs", "A", 40, 90, "après 2021", "maison", "Électricité", "très bonne",
             "2023-01-01", 50.65, 3.08, "Lille", "59350", "A", 200, 3, 2.5),
            ("dpe_neufs", "B", 70, 60, "après 2021", "appartement", "Électricité", "très bonne",
             "2023-03-03", 50.66, 3.09, "Lille", "59350", "B", 350, 6, 2.5),
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
# Familles d'énergie et nouvelles variables
# ---------------------------------------------------------------------------
def test_famille_energie_regroupe_les_variantes():
    energies = pd.Series([
        "Électricité", "Électricité d'origine renouvelable utilisée dans le bâtiment",
        "Gaz naturel", "Réseau de Chauffage urbain", "Fioul domestique",
        "Bois – Bûches", "Bois – Granulés (pellets) ou briquettes", "GPL", "Non affecté", None])
    attendu = ["Électricité", "Électricité", "Gaz naturel", "Réseau de chaleur", "Fioul",
               "Bois", "Bois", "Autre", "Autre", None]
    resultat = _famille_energie(energies)
    assert [None if pd.isna(v) else v for v in resultat] == attendu


def test_tranche_de_surface_et_famille_dans_conso_par_modalite(df):
    c = conso_par_modalite(df)
    tous = c[(c["departement"] == "Tous") & (c["origine"] == "Tous")]

    surface = tous[tous["variable"] == "tranche_surface"].set_index("modalite")["effectif"]
    assert surface["20-30 m²"] == 1 and surface["30-40 m²"] == 1 and surface["40-60 m²"] == 2
    assert surface["60-80 m²"] == 2 and surface["80-100 m²"] == 2 and surface.sum() == 8

    famille = tous[tous["variable"] == "famille_energie"].set_index("modalite")["effectif"]
    assert famille["Électricité"] == 4 and famille["Gaz naturel"] == 3 and famille["(non renseigné)"] == 1


def test_conso_par_modalite_contient_les_moustaches_de_la_boite(df):
    c = conso_par_modalite(df)
    assert {"p05", "q1", "mediane", "q3", "p95"} <= set(c.columns)
    assert (c["p05"] <= c["q1"]).all() and (c["q1"] <= c["mediane"]).all()
    assert (c["mediane"] <= c["q3"]).all() and (c["q3"] <= c["p95"]).all()


# ---------------------------------------------------------------------------
# conso_par_etiquette, cout_ges_par_etiquette, etiquette_ges_vs_dpe
# ---------------------------------------------------------------------------
def test_conso_par_etiquette_electricite(df):
    c = conso_par_etiquette(df)
    b = ligne(c, departement="Tous", origine="Tous", famille_energie="Électricité", etiquette="B")
    assert b["effectif"] == 2 and b["mediane"] == pytest.approx(65.0)     # 60 et 70


def test_conso_par_etiquette_total_energies_et_valeur_vide(df):
    c = conso_par_etiquette(df)
    tous_b = ligne(c, departement="Tous", origine="Tous", famille_energie="Tous", etiquette="B")
    assert tous_b["effectif"] == 2
    c_vide = ligne(c, departement="Tous", origine="Tous", famille_energie="(non renseigné)", etiquette="C")
    assert c_vide["effectif"] == 1 and c_vide["mediane"] == pytest.approx(150.0)


def test_cout_ges_par_etiquette(df):
    c = cout_ges_par_etiquette(df)
    g = ligne(c, departement="Tous", origine="Tous", etiquette="G")
    assert g["effectif"] == 1
    assert g["cout_par_m2_median"] == pytest.approx(80.0)    # 2000 / 25 m²
    assert g["ges_median"] == pytest.approx(90.0)
    b = ligne(c, departement="Tous", origine="Tous", etiquette="B")
    assert b["cout_par_m2_median"] == pytest.approx(6.25)    # médiane de 300/45 et 350/60
    assert b["ges_median"] == pytest.approx(5.5)


def test_etiquette_ges_vs_dpe(df):
    t = etiquette_ges_vs_dpe(df)
    assert len(t) == 3 * 7 * 7                                # 3 origines x grille 7x7
    f_f = ligne(t, origine="Tous", etiquette_dpe="F", etiquette_ges="F")
    assert f_f["pourcentage"] == pytest.approx(100.0)
    b_a = ligne(t, origine="Tous", etiquette_dpe="B", etiquette_ges="A")
    b_b = ligne(t, origine="Tous", etiquette_dpe="B", etiquette_ges="B")
    assert b_a["pourcentage"] == pytest.approx(50.0) and b_b["pourcentage"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# correlations
# ---------------------------------------------------------------------------
def test_correlations_spearman(df):
    c = correlations(df)
    assert set(c["origine"]) == {"Tous", "dpe_existants", "dpe_neufs"}
    cg = ligne(c, origine="Tous", variable_x="conso_5_usages_par_m2_ep", variable_y="emission_ges_5_usages_par_m2")
    assert cg["correlation"] == pytest.approx(1.0)            # elles augmentent ensemble
    diag = ligne(c, origine="Tous", variable_x="conso_5_usages_par_m2_ep", variable_y="conso_5_usages_par_m2_ep")
    assert diag["correlation"] == pytest.approx(1.0)


def test_correlations_symetriques(df):
    c = correlations(df)
    xy = ligne(c, origine="Tous", variable_x="surface_habitable_logement", variable_y="conso_5_usages_par_m2_ep")
    yx = ligne(c, origine="Tous", variable_x="conso_5_usages_par_m2_ep", variable_y="surface_habitable_logement")
    assert xy["correlation"] == pytest.approx(yx["correlation"])


# ---------------------------------------------------------------------------
# Temps
# ---------------------------------------------------------------------------
def test_evolution_annuelle(df):
    e = evolution_annuelle(df)
    a2021 = ligne(e, departement="Tous", origine="Tous", annee=2021)
    assert a2021["effectif"] == 2 and a2021["conso_mediane"] == pytest.approx(450.0)
    assert a2021["part_f_g"] == pytest.approx(100.0)
    a2022 = ligne(e, departement="Tous", origine="Tous", annee=2022)
    assert a2022["effectif"] == 3 and a2022["conso_mediane"] == pytest.approx(200.0)
    assert a2022["part_f_g"] == pytest.approx(0.0)
    a2023 = ligne(e, departement="Tous", origine="Tous", annee=2023)
    assert a2023["effectif"] == 3 and a2023["conso_mediane"] == pytest.approx(60.0)


def test_couverture_temporelle(df):
    c = ligne(couverture_temporelle(df), departement="Tous", origine="Tous")
    assert c["nb_logements"] == 8
    assert c["date_min"] == pd.Timestamp("2021-03-01") and c["date_max"] == pd.Timestamp("2023-05-05")


# ---------------------------------------------------------------------------
# Carte et nuage de points
# ---------------------------------------------------------------------------
def test_communes_filtre_les_petites_communes(df):
    with patch.object(analysis, "MIN_LOGEMENTS_COMMUNE", 2):
        c = communes(df)
    paris = ligne(c, code_insee="75101", origine="Tous")
    assert paris["effectif"] == 3 and paris["conso_mediane"] == pytest.approx(400.0)
    assert paris["part_f_g"] == pytest.approx(66.7)
    assert "75102" not in set(c["code_insee"])               # 1 seul logement : écartée
    lille = ligne(c, code_insee="59350", origine="Tous")
    assert lille["effectif"] == 4 and lille["conso_mediane"] == pytest.approx(110.0)


def test_communes_seuil_par_defaut_ecarte_tout_sur_un_petit_jeu(df):
    assert len(communes(df)) == 0                            # aucune commune n'atteint 30 logements


def test_echantillon_points_reproductible_et_equilibre(df):
    with patch.object(analysis, "POINTS_PAR_DEPARTEMENT", 2):
        a = echantillon_points(df)
        b = echantillon_points(df)
    assert len(a) == 4 and a.groupby("departement").size().eq(2).all()
    pd.testing.assert_frame_equal(a, b)                      # même échantillon à chaque fois


def test_echantillon_points_ecarte_les_logements_sans_position(df):
    df = df.copy()
    df.loc[0, "latitude"] = None
    a = echantillon_points(df)
    assert len(a) == 7


# ---------------------------------------------------------------------------
# Table légère de logements
# ---------------------------------------------------------------------------
def test_table_logements(df):
    t = table_logements(df)
    assert len(t) == 8
    assert {"departement", "origine", "etiquette_dpe", "annee_reception", "famille_energie",
            "tranche_surface", "latitude", "longitude"} <= set(t.columns)
    assert "date_reception_dpe" not in t.columns             # table légère : pas toutes les colonnes
    assert isinstance(t["etiquette_dpe"].dtype, pd.CategoricalDtype)
    assert t["conso_5_usages_par_m2_ep"].sum() == pytest.approx(1720.0)


# ---------------------------------------------------------------------------
# Qualité des données
# ---------------------------------------------------------------------------
def test_qualite_donnees_taux_de_cases_vides():
    q = qualite_donnees(donnees())
    energie = ligne(q, departement="Tous", colonne="type_energie_principale_chauffage")
    assert energie["pct_manquant"] == pytest.approx(12.5)    # 1 case vide sur 8
    energie59 = ligne(q, departement="59", colonne="type_energie_principale_chauffage")
    assert energie59["pct_manquant"] == pytest.approx(25.0)  # 1 sur 4
    assert ligne(q, departement="75", colonne="type_energie_principale_chauffage")["pct_manquant"] == 0


def test_qualite_donnees_colonne_absente_d_un_departement():
    data = donnees()
    data["59"] = data["59"].drop(columns="cout_total_5_usages")
    q = qualite_donnees(data)
    assert not ligne(q, departement="59", colonne="cout_total_5_usages")["presente"]
    assert ligne(q, departement="59", colonne="cout_total_5_usages")["pct_manquant"] == pytest.approx(100.0)
    assert ligne(q, departement="75", colonne="cout_total_5_usages")["presente"]
    assert ligne(q, departement="Tous", colonne="cout_total_5_usages")["pct_manquant"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Résumé des variables numériques
# ---------------------------------------------------------------------------
def test_stats_numeriques_surface(df):
    s = stats_numeriques(df)
    # surfaces : 25, 30, 45, 50, 60, 70, 80, 90
    tous = ligne(s, variable="surface_habitable_logement", departement="Tous", origine="Tous")
    assert tous["effectif"] == 8
    assert tous["nb_manquants"] == 0
    assert tous["moyenne"] == pytest.approx(56.25)
    assert tous["mediane"] == pytest.approx(55.0)
    assert tous["minimum"] == 25
    assert tous["maximum"] == 90
    # dept 75 : 25, 30, 45, 50
    d75 = ligne(s, variable="surface_habitable_logement", departement="75", origine="Tous")
    assert d75["moyenne"] == pytest.approx(37.5)
    assert d75["mediane"] == pytest.approx(37.5)


def test_stats_numeriques_contient_toutes_les_variables(df):
    s = stats_numeriques(df)
    assert set(s["variable"]) == {"conso_5_usages_par_m2_ep", "surface_habitable_logement",
                                  "hauteur_sous_plafond", "emission_ges_5_usages_par_m2",
                                  "cout_total_5_usages"}


def test_stats_numeriques_compte_les_valeurs_manquantes(df):
    df = df.copy()
    df.loc[0, "surface_habitable_logement"] = None
    tous = ligne(stats_numeriques(df), variable="surface_habitable_logement",
                 departement="Tous", origine="Tous")
    assert tous["effectif"] == 7
    assert tous["nb_manquants"] == 1


def test_stats_numeriques_sans_colonnes_numeriques_tableau_vide(df):
    s = stats_numeriques(df[["code_departement_ban", "origine", "etiquette_dpe"]])
    assert len(s) == 0
    assert "mediane" in s.columns


# ---------------------------------------------------------------------------
# Aperçu des données (page Contexte)
# ---------------------------------------------------------------------------
def test_apercu_donnees_lignes_et_colonnes():
    a = apercu_donnees(donnees())
    tous = ligne(a, departement="Tous")
    assert tous["nb_lignes"] == 8
    assert tous["nb_colonnes"] == 18
    assert ligne(a, departement="75")["nb_lignes"] == 4
    assert ligne(a, departement="59")["nb_lignes"] == 4


def test_apercu_donnees_types_de_colonnes():
    tous = ligne(apercu_donnees(donnees()), departement="Tous")
    # numériques : conso, surface, latitude, longitude, coût, GES, hauteur ; date : 1
    assert tous["nb_numeriques"] == 7
    assert tous["nb_dates"] == 1
    assert tous["nb_texte"] == 10
    assert tous["nb_numeriques"] + tous["nb_dates"] + tous["nb_texte"] == tous["nb_colonnes"]


def test_apercu_donnees_colonne_absente_d_un_departement():
    data = donnees()
    data["59"] = data["59"].drop(columns="cout_total_5_usages")
    a = apercu_donnees(data)
    assert ligne(a, departement="59")["nb_colonnes"] == 17
    assert ligne(a, departement="75")["nb_colonnes"] == 18
    assert ligne(a, departement="Tous")["nb_colonnes"] == 18     # comptée une seule fois


def test_apercu_donnees_sans_donnees_tableau_vide():
    a = apercu_donnees({})
    assert len(a) == 0
    assert "nb_colonnes" in a.columns


# ---------------------------------------------------------------------------
# Bilan du nettoyage (page Contexte)
# ---------------------------------------------------------------------------
def rapport():
    """Rapport tel qu'enregistré par le nettoyage (DataPreprocessor.rapport())."""
    return {
        "75": {"bilan": [["Données brutes", 100], ["Doublons supprimés", 90], ["Étiquettes A-G", 90],
                         ["Surface 5-500 m²", 80]],
               "colonnes_retirees": [["colonne_a", 95.5], ["colonne_b", 99.0]]},
        "59": {"bilan": [["Données brutes", 50], ["Doublons supprimés", 50], ["Étiquettes A-G", 45],
                         ["Surface 5-500 m²", 40]],
               "colonnes_retirees": [["colonne_a", 85.0]]},
    }


def test_bilan_nettoyage_lignes_et_lignes_retirees_par_etape():
    b = bilan_nettoyage(rapport())
    assert ligne(b, departement="75", etape="Données brutes")["lignes_retirees"] == 0
    assert ligne(b, departement="75", etape="Doublons supprimés")["lignes_retirees"] == 10
    assert ligne(b, departement="75", etape="Surface 5-500 m²")["lignes"] == 80
    assert ligne(b, departement="75", etape="Surface 5-500 m²")["lignes_retirees"] == 10
    assert ligne(b, departement="59", etape="Étiquettes A-G")["lignes_retirees"] == 5


def test_bilan_nettoyage_tous_additionne_les_departements():
    b = bilan_nettoyage(rapport())
    assert ligne(b, departement="Tous", etape="Données brutes")["lignes"] == 150
    assert ligne(b, departement="Tous", etape="Doublons supprimés")["lignes_retirees"] == 10
    assert ligne(b, departement="Tous", etape="Surface 5-500 m²")["lignes"] == 120
    assert ligne(b, departement="Tous", etape="Surface 5-500 m²")["lignes_retirees"] == 15


def test_bilan_nettoyage_garde_l_ordre_des_etapes():
    b = bilan_nettoyage(rapport())
    d75 = b[b["departement"] == "75"]
    assert list(d75["etape"]) == ["Données brutes", "Doublons supprimés", "Étiquettes A-G",
                                  "Surface 5-500 m²"]
    assert list(d75["ordre"]) == [0, 1, 2, 3]


def test_bilan_nettoyage_sans_rapport_tableau_vide():
    for rien in (None, {}):
        b = bilan_nettoyage(rien)
        assert len(b) == 0
        assert "lignes_retirees" in b.columns


def test_colonnes_retirees_par_departement_triees_par_taux():
    c = colonnes_retirees(rapport())
    d75 = c[c["departement"] == "75"]
    assert list(d75["colonne"]) == ["colonne_b", "colonne_a"]       # 99 % puis 95,5 %
    assert ligne(c, departement="59", colonne="colonne_a")["pct_manquant"] == pytest.approx(85.0)
    assert len(c) == 3


def test_colonnes_retirees_sans_rapport_ou_sans_colonne_tableau_vide():
    assert len(colonnes_retirees(None)) == 0
    assert len(colonnes_retirees({"75": {"bilan": [], "colonnes_retirees": []}})) == 0
    assert "pct_manquant" in colonnes_retirees(None).columns


def test_compute_all_avec_rapport_de_nettoyage():
    resultats = StatAnalyzer().compute_all(donnees(), rapport())
    assert len(resultats["bilan_nettoyage"]) == 12                 # (2 départements + Tous) x 4 étapes
    assert len(resultats["colonnes_retirees"]) == 3


# ---------------------------------------------------------------------------
# StatAnalyzer : l'ensemble
# ---------------------------------------------------------------------------
def test_compute_all_calcule_tout_et_les_analyses_ont_des_lignes():
    analyzer = StatAnalyzer()
    resultats = analyzer.compute_all(donnees())
    assert set(resultats) == set(analyzer.noms())
    assert set(ANALYSES) <= set(resultats)
    # communes : aucune commune n'atteint 30 logements ; les deux autres : pas de rapport de nettoyage
    vides_attendus = {"communes", "bilan_nettoyage", "colonnes_retirees"}
    for nom, tableau in resultats.items():
        assert isinstance(tableau, pd.DataFrame), nom
        if nom not in vides_attendus:
            assert len(tableau) > 0, nom


def test_compute_all_sans_colonnes_optionnelles_ne_plante_pas():
    """Si un rafraîchissement supprime des colonnes, les analyses concernées sont vides."""
    data = {k: v.drop(columns=["latitude", "longitude", "etiquette_ges", "cout_total_5_usages",
                               "date_reception_dpe"]) for k, v in donnees().items()}
    resultats = StatAnalyzer().compute_all(data)
    for nom in ("communes", "echantillon_points", "etiquette_ges_vs_dpe", "cout_ges_par_etiquette",
                "evolution_annuelle", "couverture_temporelle"):
        assert len(resultats[nom]) == 0, nom
    assert len(resultats["kpi_globaux"]) > 0


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
