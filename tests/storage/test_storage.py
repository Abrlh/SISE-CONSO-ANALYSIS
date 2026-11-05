import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.storage.storage import LocalStorage, Storage


class TestLocalStorage(unittest.TestCase):
    def setUp(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.root = Path(tmp_dir.name)
        self.storage = LocalStorage(self.root)
        self.df = pd.DataFrame({"code": ["01", "2A"], "conso": [120.5, 98.0]})

    def test_storage_is_abstract(self):
        with self.assertRaises(TypeError):
            Storage()

    def test_save_then_load_returns_same_dataframe(self):
        self.storage.save(self.df, "raw/snapshot.parquet")
        pd.testing.assert_frame_equal(self.storage.load("raw/snapshot.parquet"), self.df)

    def test_save_creates_subfolder(self):
        self.storage.save(self.df, "processed/snapshot.parquet")
        self.assertTrue((self.root / "processed" / "snapshot.parquet").is_file())

    def test_load_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.storage.load("raw/absent.parquet")


if __name__ == "__main__":
    unittest.main()
