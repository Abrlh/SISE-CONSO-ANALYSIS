import pandas as pd
import pytest

from src.storage.storage import LocalStorage


def test_alleger_garde_les_colonnes_demandees(tmp_path):
    stockage = LocalStorage(tmp_path)
    df = pd.DataFrame({"a": [1, 2], "b": [3.0, 4.0], "c": ["x", "y"]})
    stockage.save(df, "snap/59.parquet")
    assert stockage.alleger("snap/59.parquet", ["c", "a"]) == (3, 2)
    # l'ordre d'origine est conservé
    pd.testing.assert_frame_equal(stockage.load("snap/59.parquet"), df[["a", "c"]])


def test_alleger_sans_ecrire_ne_modifie_rien(tmp_path):
    stockage = LocalStorage(tmp_path)
    df = pd.DataFrame({"a": [1, 2], "b": [3.0, 4.0]})
    stockage.save(df, "snap/59.parquet")
    assert stockage.alleger("snap/59.parquet", ["a"], ecrire=False) == (2, 1)
    pd.testing.assert_frame_equal(stockage.load("snap/59.parquet"), df)


def test_alleger_refuse_une_colonne_absente(tmp_path):
    stockage = LocalStorage(tmp_path)
    df = pd.DataFrame({"a": [1, 2], "b": [3.0, 4.0]})
    stockage.save(df, "snap/59.parquet")
    with pytest.raises(KeyError):
        stockage.alleger("snap/59.parquet", ["a", "zzz"])
    pd.testing.assert_frame_equal(stockage.load("snap/59.parquet"), df)