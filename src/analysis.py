"""StatAnalyzer : calcule les statistiques descriptives des DPE (KPI, répartitions).

Ce fichier n'importe jamais streamlit et ne dessine aucun graphique : il reçoit un DataFrame
pandas et renvoie des nombres, des dictionnaires ou des DataFrame. L'affichage est fait dans app/.
"""

import pandas as pd

# Colonnes du fichier data/processed (voir docs/colonnes_retenues.csv)
COL_ETIQUETTE = "etiquette_dpe"
COL_CONSO = "conso_5_usages_par_m2_ep"  # kWh/m²/an, énergie primaire
COL_DEPARTEMENT = "code_departement_ban"

ETIQUETTES = ["A", "B", "C", "D", "E", "F", "G"]
UNITE_CONSO = "kWh/m²/an"

# Noms lisibles des départements du snapshot actuel (un code inconnu est affiché tel quel)
NOMS_DEPARTEMENTS = {"59": "Nord", "69": "Rhône", "75": "Paris"}


class StatAnalyzer():
    """Statistiques descriptives. Chaque méthode reçoit un DataFrame et ne le modifie jamais."""

    def __init__(self):
        pass

    # ------------------------------------------------------------------ outils internes

    def __verifier_colonnes(self, df: pd.DataFrame, colonnes: list) -> None:
        """Lève une erreur claire si une colonne attendue est absente du tableau."""
        manquantes = [c for c in colonnes if c not in df.columns]
        if manquantes:
            raise ValueError(
                f"Colonnes introuvables dans les données : {manquantes}. "
                "Les données prétraitées ne sont peut-être pas à jour (voir docs/nettoyage_donnees.md)."
            )

    def __etiquettes(self, df: pd.DataFrame) -> pd.Series:
        """Colonne étiquette en catégorie ordonnée A < B < ... < G (toute autre valeur devient manquante)."""
        type_etiquette = pd.CategoricalDtype(categories=ETIQUETTES, ordered=True)
        return df[COL_ETIQUETTE].astype(type_etiquette)

    def __nombre(self, valeur):
        """Convertit en float, ou en None si la valeur est manquante (la page affiche alors « n/a »)."""
        return None if pd.isna(valeur) else float(valeur)

    # ------------------------------------------------------------------ méthodes publiques

    def departements(self, df: pd.DataFrame) -> list:
        """Codes des départements présents dans les données, triés (liste vide si la colonne n'existe pas)."""
        if COL_DEPARTEMENT not in df.columns:
            return []
        return sorted(str(d) for d in df[COL_DEPARTEMENT].dropna().unique())

    def kpi(self, df: pd.DataFrame) -> dict:
        """Indicateurs clés de la page Contexte, dans un dictionnaire {nom: valeur}."""
        self.__verifier_colonnes(df, [COL_ETIQUETTE, COL_CONSO])
        etiquette = self.__etiquettes(df)
        valides = etiquette.dropna()  # lignes dont l'étiquette est valide
        conso = df[COL_CONSO]

        # Part des logements classés F ou G, parmi ceux qui ont une étiquette valide
        part_fg = valides.isin(["F", "G"]).mean() if len(valides) else None

        # Étiquette la plus fréquente
        dominante = str(valides.value_counts().idxmax()) if len(valides) else None

        # Écart de consommation moyenne entre les logements G et A
        moyennes = df.groupby(etiquette, observed=True)[COL_CONSO].mean()
        if "G" in moyennes.index and "A" in moyennes.index:
            ecart = float(moyennes["G"] - moyennes["A"])
        else:
            ecart = None

        return {
            "nb_dpe": int(len(df)),
            "conso_moyenne": self.__nombre(conso.mean()),
            "conso_mediane": self.__nombre(conso.median()),
            "part_fg": self.__nombre(part_fg),
            "etiquette_frequente": dominante,
            "ecart_g_vs_a": ecart,
        }

    def repartition_etiquettes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Nombre de logements par étiquette, dans l'ordre A..G (une ligne par étiquette)."""
        self.__verifier_colonnes(df, [COL_ETIQUETTE])
        comptes = self.__etiquettes(df).value_counts().sort_index()
        return pd.DataFrame(
            {"Nombre de DPE": comptes.values},
            index=[str(e) for e in comptes.index],
        )

    def conso_par_etiquette(self, df: pd.DataFrame) -> pd.DataFrame:
        """Consommation moyenne de chaque étiquette : montre le lien entre étiquette et consommation."""
        self.__verifier_colonnes(df, [COL_ETIQUETTE, COL_CONSO])
        moyennes = df.groupby(self.__etiquettes(df), observed=True)[COL_CONSO].mean()
        return pd.DataFrame(
            {f"Conso moyenne ({UNITE_CONSO})": moyennes.values},
            index=[str(e) for e in moyennes.index],
        )
