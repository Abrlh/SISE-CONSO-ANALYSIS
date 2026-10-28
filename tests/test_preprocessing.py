"""
Tests unitaires du nettoyage (src/preprocessing.py).

Principe : on fabrique de tout petits tableaux avec des cas pièges (valeurs juste
dans la limite, juste au-dessus, manquantes...) et on vérifie qu'une règle fait
exactement ce qu'elle doit. Si quelqu'un change un seuil ou une règle par erreur,
un test casse et le prévient.

Lancer : python -m pytest tests/test_preprocessing.py -v
"""
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src import preprocessing as prep
from src.preprocessing import (
    DataPreprocessor,
    exclure_immeubles,
    extraire_coordonnees,
    filtrer_consommation,
    filtrer_emissions_ges,
    filtrer_etiquettes,
    filtrer_surface,
    nettoyer,
    nettoyer_hauteur,
    retirer_colonnes_vides,
    supprimer_doublons,
    supprimer_espaces,
    supprimer_manquants_cles,
    verifier_colonnes_obligatoires,
)


# ---------------------------------------------------------------------------
# Outil : fabriquer un petit tableau de logements valides
# ---------------------------------------------------------------------------
def logements(n=10, **colonnes):
    """n logements valides. On remplace une colonne en passant une liste de n valeurs
    (ex. surface_habitable_logement=[3, 5, 60, ...])."""
    df = pd.DataFrame({
        "numero_dpe": [f"id{i}" for i in range(n)],
        "etiquette_dpe": ["C"] * n,
        "conso_5_usages_par_m2_ep": [150.0] * n,
        "surface_habitable_logement": [60.0] * n,
        "emission_ges_5_usages_par_m2": [20.0] * n,
        "hauteur_sous_plafond": [2.5] * n,
        "type_batiment": ["maison"] * n,
    })
    for nom, valeurs in colonnes.items():
        df[nom] = valeurs
    return df


# ---------------------------------------------------------------------------
# Colonnes indispensables
# ---------------------------------------------------------------------------
def test_colonnes_obligatoires_presentes_ne_change_rien():
    df = logements(3)
    assert verifier_colonnes_obligatoires(df) is df


def test_colonne_obligatoire_absente_arrete_avec_message_clair():
    df = logements(3).drop(columns="etiquette_dpe")
    with pytest.raises(ValueError, match="etiquette_dpe"):
        verifier_colonnes_obligatoires(df)


# ---------------------------------------------------------------------------
# Règles qui retirent des lignes
# ---------------------------------------------------------------------------
def test_doublons_un_seul_dpe_par_numero():
    df = logements(3, numero_dpe=["a", "a", "b"])
    assert list(supprimer_doublons(df)["numero_dpe"]) == ["a", "b"]


def test_immeubles_exclus_par_defaut():
    df = logements(3, type_batiment=["maison", "immeuble", "appartement"])
    assert list(exclure_immeubles(df)["type_batiment"]) == ["maison", "appartement"]


def test_immeubles_gardes_si_la_liste_est_vide():
    df = logements(3, type_batiment=["maison", "immeuble", "appartement"])
    with patch.object(prep, "TYPES_BATIMENT_EXCLUS", []):
        assert len(exclure_immeubles(df)) == 3


def test_immeubles_sans_colonne_type_batiment_ne_plante_pas():
    df = logements(3).drop(columns="type_batiment")
    assert len(exclure_immeubles(df)) == 3


def test_manquants_cles_retires():
    df = logements(
        4,
        etiquette_dpe=["C", None, "C", "C"],
        conso_5_usages_par_m2_ep=[150.0, 150.0, np.nan, 150.0],
        surface_habitable_logement=[60.0, 60.0, 60.0, np.nan],
    )
    assert list(supprimer_manquants_cles(df)["numero_dpe"]) == ["id0"]


def test_etiquettes_a_g_gardees_les_autres_retirees():
    df = logements(4, etiquette_dpe=["A", "G", "H", "Z"])
    assert list(filtrer_etiquettes(df)["etiquette_dpe"]) == ["A", "G"]


def test_etiquettes_espaces_et_minuscules_corriges():
    df = logements(2, etiquette_dpe=[" b ", "d"])
    assert list(filtrer_etiquettes(df)["etiquette_dpe"]) == ["B", "D"]


def test_surface_bornes_5_et_500_incluses():
    # 4 -> retiré ; 5 et 500 -> gardés ; 501 -> retiré
    df = logements(4, surface_habitable_logement=[4.0, 5.0, 500.0, 501.0])
    assert list(filtrer_surface(df)["surface_habitable_logement"]) == [5.0, 500.0]


def test_consommation_zero_et_au_dessus_de_1000_retires():
    # 0 -> retiré ; 1000 -> gardé ; 1001 -> retiré ; manquant -> retiré
    df = logements(4, conso_5_usages_par_m2_ep=[0.0, 1000.0, 1001.0, np.nan])
    assert list(filtrer_consommation(df)["conso_5_usages_par_m2_ep"]) == [1000.0]


def test_ges_au_dessus_de_1000_retire_mais_manquant_conserve():
    df = logements(3, emission_ges_5_usages_par_m2=[1000.0, 1001.0, np.nan])
    assert list(filtrer_emissions_ges(df)["numero_dpe"]) == ["id0", "id2"]


def test_ges_colonne_absente_ne_plante_pas():
    df = logements(3).drop(columns="emission_ges_5_usages_par_m2")
    assert len(filtrer_emissions_ges(df)) == 3


# ---------------------------------------------------------------------------
# Règles qui gardent la ligne en corrigeant la valeur
# ---------------------------------------------------------------------------
def test_coordonnees_en_france_extraites_en_deux_colonnes():
    df = logements(1, _geopoint=["48.85,2.35"])
    out = extraire_coordonnees(df)
    assert out.loc[0, "latitude"] == pytest.approx(48.85)
    assert out.loc[0, "longitude"] == pytest.approx(2.35)
    assert "_geopoint" not in out.columns


def test_coordonnees_hors_de_france_deviennent_manquantes_ligne_conservee():
    # Position erronée (ex. hors de France) : ni latitude ni longitude, mais la ligne reste
    df = logements(2, _geopoint=["48.85,2.35", "10.0,-60.0"])
    out = extraire_coordonnees(df)
    assert len(out) == 2
    assert pd.isna(out.loc[1, "latitude"]) and pd.isna(out.loc[1, "longitude"])
    assert not pd.isna(out.loc[0, "latitude"])


def test_coordonnees_illisibles_deviennent_manquantes():
    df = logements(2, _geopoint=["pas,des,nombres", None])
    out = extraire_coordonnees(df)
    assert len(out) == 2
    assert out["latitude"].isna().all()


def test_coordonnees_sans_colonne_geopoint_ne_plante_pas():
    df = logements(2)
    assert extraire_coordonnees(df).equals(df)


def test_hauteur_hors_plage_devient_manquante_ligne_conservee():
    # 250 (cm saisis par erreur) et 1.0 -> manquants ; 1.8 et 5 -> gardés
    df = logements(4, hauteur_sous_plafond=[250.0, 1.0, 1.8, 5.0])
    out = nettoyer_hauteur(df)
    assert len(out) == 4
    assert out["hauteur_sous_plafond"].isna().tolist() == [True, True, False, False]


def test_espaces_debut_et_fin_supprimes_dans_toutes_les_colonnes_texte():
    df = logements(2, type_batiment=[" maison ", "appartement  "], autre_texte=[" a", "b "])
    out = supprimer_espaces(df)
    assert list(out["type_batiment"]) == ["maison", "appartement"]
    assert list(out["autre_texte"]) == ["a", "b"]


# ---------------------------------------------------------------------------
# Colonnes trop vides
# ---------------------------------------------------------------------------
def test_colonne_vide_a_plus_de_80_pct_retiree():
    # 9 vides sur 10 = 90 % -> retirée
    df = logements(10, tres_vide=[1] + [np.nan] * 9)
    retirees = []
    out = retirer_colonnes_vides(df, retirees)
    assert "tres_vide" not in out.columns
    assert retirees == [("tres_vide", 90.0)]


def test_colonne_vide_a_exactement_80_pct_conservee():
    # 8 vides sur 10 = 80 % pile -> la règle est "plus de 80 %" : conservée
    df = logements(10, limite=[1, 2] + [np.nan] * 8)
    assert "limite" in retirer_colonnes_vides(df).columns


def test_colonne_obligatoire_jamais_retiree_meme_vide():
    df = logements(10, numero_dpe=[np.nan] * 10)
    assert "numero_dpe" in retirer_colonnes_vides(df).columns


def test_retirer_colonnes_vides_ne_remplace_aucune_valeur_manquante():
    df = logements(10, un_peu_vide=[1, 2, 3, 4, 5, 6, np.nan, np.nan, np.nan, np.nan])
    out = retirer_colonnes_vides(df)
    assert out["un_peu_vide"].isna().sum() == 4


# ---------------------------------------------------------------------------
# Le nettoyage complet
# ---------------------------------------------------------------------------
def donnees_brutes():
    """12 lignes : 6 valides + 6 qui doivent disparaître ou être corrigées."""
    n = 12
    return logements(
        n,
        # ligne 0 doublon de ligne 1 ; ligne 2 = immeuble
        numero_dpe=["a", "a"] + [f"id{i}" for i in range(2, n)],
        type_batiment=["maison", "maison", "immeuble"] + ["maison"] * (n - 3),
        etiquette_dpe=["C", "C", "C", "Z", "C", "C", "C", "C", "C", "C", "C", "C"],  # ligne 3 invalide
        surface_habitable_logement=[60.0] * 4 + [3.0] + [60.0] * 7,                    # ligne 4 trop petite
        conso_5_usages_par_m2_ep=[150.0] * 5 + [2000.0] + [150.0] * 6,                 # ligne 5 trop forte
        hauteur_sous_plafond=[2.5] * 6 + [250.0] + [2.5] * 5,                          # ligne 6 corrigée, gardée
        _geopoint=["48.85,2.35"] * 7 + ["10.0,-60.0"] + ["48.85,2.35"] * 4,            # ligne 7 corrigée, gardée
        colonne_nouvelle=["x"] * n,                                                     # colonne inconnue du code
        presque_vide=[1] + [np.nan] * (n - 1),                                          # sera retirée
    )


def test_nettoyage_complet_lignes_retenues():
    out = nettoyer(donnees_brutes())
    # 12 - 1 doublon - 1 immeuble - 1 étiquette - 1 surface - 1 conso = 7 lignes
    assert len(out) == 7
    assert out.index.tolist() == list(range(7))  # index remis à zéro


def test_nettoyage_complet_corrections_sans_perte_de_ligne():
    out = nettoyer(donnees_brutes())
    assert out["hauteur_sous_plafond"].isna().sum() == 1   # 250 m -> manquant
    assert out["latitude"].isna().sum() == 1               # position erronée -> manquante
    assert "_geopoint" not in out.columns


def test_nettoyage_garde_les_colonnes_inconnues_et_retire_les_presque_vides():
    colonnes_retirees = []
    out = nettoyer(donnees_brutes(), colonnes_retirees=colonnes_retirees)
    assert "colonne_nouvelle" in out.columns          # une nouvelle colonne passe automatiquement
    assert "presque_vide" not in out.columns
    assert [c for c, _ in colonnes_retirees] == ["presque_vide"]


def test_nettoyage_ne_remplace_pas_les_valeurs_manquantes():
    out = nettoyer(donnees_brutes())
    assert out.isna().sum().sum() > 0   # les trous (hauteur, latitude, longitude) restent


def test_nettoyage_remplit_le_bilan_dans_l_ordre():
    bilan = []
    nettoyer(donnees_brutes(), bilan=bilan)
    noms = [nom for nom, _ in bilan]
    lignes = [n for _, n in bilan]
    assert noms[0] == "Données brutes" and lignes[0] == 12
    assert lignes == sorted(lignes, reverse=True)   # le nombre de lignes ne fait que diminuer
    assert lignes[-1] == 7


def test_nettoyage_ne_modifie_pas_le_tableau_d_origine():
    brut = donnees_brutes()
    copie = brut.copy(deep=True)
    nettoyer(brut)
    pd.testing.assert_frame_equal(brut, copie)


def test_nettoyage_sans_colonne_indispensable_arrete_avec_message():
    with pytest.raises(ValueError, match="numero_dpe"):
        nettoyer(donnees_brutes().drop(columns="numero_dpe"))


# ---------------------------------------------------------------------------
# La classe DataPreprocessor (fusion neufs + existants, un département à la fois)
# ---------------------------------------------------------------------------
def test_preprocessor_fusionne_existants_et_neufs_avec_origine():
    datasets = {"75": {"dpe_existants": logements(3), "dpe_neufs": logements(2)}}
    fusion = DataPreprocessor().fusionner(datasets)["75"]
    assert len(fusion) == 5
    assert fusion["origine"].value_counts().to_dict() == {"dpe_existants": 3, "dpe_neufs": 2}


def test_preprocessor_process_traite_chaque_departement_separement():
    p = DataPreprocessor()
    datasets = {
        "75": {"dpe_existants": logements(10), "dpe_neufs": logements(5).assign(numero_dpe=lambda d: "n" + d["numero_dpe"])},
        "59": {"dpe_existants": logements(8), "dpe_neufs": logements(0)},
    }
    out = p.process(datasets)
    assert set(out) == {"59", "75"}
    assert len(out["75"]) == 15 and len(out["59"]) == 8
    assert set(p.bilans) == {"59", "75"}
    assert set(p.colonnes_retirees) == {"59", "75"}
    assert p.bilans["75"].loc["Données brutes", "lignes"] == 15


def test_preprocessor_sans_nettoyage_renvoie_seulement_la_fusion():
    datasets = {"75": {"dpe_existants": logements(3), "dpe_neufs": logements(2)}}
    out = DataPreprocessor(appliquer_nettoyage=False).process(datasets)
    assert len(out["75"]) == 5


def test_preprocessor_rapport_s_ecrit_en_json_et_contient_le_bilan():
    import json
    p = DataPreprocessor()
    p.process({"75": {"dpe_existants": logements(10, colonne_vide=[None] * 10),
                      "dpe_neufs": logements(0)}})
    r = p.rapport()
    json.dumps(r)                                               # doit être écrivable
    assert r["75"]["bilan"][0] == ["Données brutes", 10]
    assert r["75"]["colonnes_retirees"] == [["colonne_vide", 100.0]]


def test_preprocessor_rapport_vide_avant_process():
    assert DataPreprocessor().rapport() == {}
