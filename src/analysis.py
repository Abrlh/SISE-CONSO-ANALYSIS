"""StatAnalyzer : calcule les statistiques descriptives des DPE (KPI, répartitions).

Ce fichier n'importe jamais streamlit et ne dessine aucun graphique : il reçoit un DataFrame
pandas et renvoie des nombres, des dictionnaires ou des DataFrame. L'affichage est fait dans app/.
"""

import numpy as np
import pandas as pd

# Colonnes du fichier data/processed (voir docs/colonnes_retenues.csv)
COL_ETIQUETTE = "etiquette_dpe"
COL_CONSO = "conso_5_usages_par_m2_ep"  # kWh/m²/an, énergie primaire
COL_DEPARTEMENT = "code_departement_ban"
COL_SURFACE = "surface_habitable_logement"  # m²
COL_ORIGINE = "origine"  # logement neuf ou existant
COL_PERIODE = "periode_construction"

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

    def options_filtres(self, df: pd.DataFrame) -> dict:
        """Valeurs proposées dans les filtres de la page Visualisations."""
        self.__verifier_colonnes(df, [COL_ETIQUETTE, COL_SURFACE, COL_ORIGINE, COL_PERIODE])
        surface = df[COL_SURFACE]
        return {
            "departements": self.departements(df),
            "etiquettes": [e for e in ETIQUETTES if e in set(df[COL_ETIQUETTE].dropna().astype(str))],
            "origines": sorted(str(o) for o in df[COL_ORIGINE].dropna().unique()),
            "periodes": sorted(str(p) for p in df[COL_PERIODE].dropna().unique()),
            "surface_min": int(np.floor(surface.min())),
            "surface_max": int(np.ceil(surface.max())),
        }

    def filtrer(self, df: pd.DataFrame, filtres: dict) -> pd.DataFrame:
        """Lignes qui respectent les filtres. Une clé absente ou égale à None signifie « pas de filtre ».

        Clés possibles : departements, etiquettes, origines, periodes (listes de valeurs),
        surface (tuple (min, max) en m²), sans_extremes (True = retire le 1 % de consommations les plus élevées).
        """
        colonnes_listes = {
            "departements": COL_DEPARTEMENT,
            "etiquettes": COL_ETIQUETTE,
            "origines": COL_ORIGINE,
            "periodes": COL_PERIODE,
        }
        masque = pd.Series(True, index=df.index)
        for cle, colonne in colonnes_listes.items():
            if filtres.get(cle) is not None:
                self.__verifier_colonnes(df, [colonne])
                masque &= df[colonne].isin(filtres[cle])
        if filtres.get("surface") is not None:
            self.__verifier_colonnes(df, [COL_SURFACE])
            minimum, maximum = filtres["surface"]
            masque &= df[COL_SURFACE].between(minimum, maximum)
        if filtres.get("sans_extremes"):
            self.__verifier_colonnes(df, [COL_CONSO])
            masque &= df[COL_CONSO] <= df[COL_CONSO].quantile(0.99)
        return df[masque]

    def histogramme_conso(self, df: pd.DataFrame, nb_classes: int = 30) -> pd.DataFrame:
        """Nombre de logements par tranche de consommation (l'index est le centre de chaque tranche)."""
        self.__verifier_colonnes(df, [COL_CONSO])
        valeurs = df[COL_CONSO].dropna()
        if valeurs.empty:
            return pd.DataFrame({"Nombre de DPE": []})
        comptes, bords = np.histogram(valeurs, bins=nb_classes)
        centres = ((bords[:-1] + bords[1:]) / 2).round(1)
        return pd.DataFrame({"Nombre de DPE": comptes}, index=centres)

    def boites_conso_par_etiquette(self, df: pd.DataFrame) -> pd.DataFrame:
        """Chiffres d'une boîte à moustaches par étiquette : moustaches, quartiles et médiane.

        Les moustaches vont jusqu'à 1,5 fois l'écart interquartile, sans dépasser le minimum et le maximum.
        """
        self.__verifier_colonnes(df, [COL_ETIQUETTE, COL_CONSO])
        groupes = df.groupby(self.__etiquettes(df), observed=True)[COL_CONSO]
        q1 = groupes.quantile(0.25)
        q3 = groupes.quantile(0.75)
        ecart = q3 - q1
        boites = pd.DataFrame({
            "etiquette": [str(e) for e in q1.index],
            "bas": np.maximum(groupes.min().values, (q1 - 1.5 * ecart).values),
            "q1": q1.values,
            "mediane": groupes.median().values,
            "q3": q3.values,
            "haut": np.minimum(groupes.max().values, (q3 + 1.5 * ecart).values),
        })
        return boites

    def nuage_surface_conso(self, df: pd.DataFrame, nb_points: int = 3000) -> pd.DataFrame:
        """Échantillon aléatoire de logements (surface, consommation, étiquette) pour un nuage de points."""
        self.__verifier_colonnes(df, [COL_SURFACE, COL_CONSO, COL_ETIQUETTE])
        echantillon = df.sample(min(nb_points, len(df)), random_state=0)
        resultat = echantillon[[COL_SURFACE, COL_CONSO, COL_ETIQUETTE]].copy()
        resultat[COL_ETIQUETTE] = resultat[COL_ETIQUETTE].astype(str)
        return resultat

    def conso_par_departement(self, df: pd.DataFrame) -> pd.DataFrame:
        """Consommation moyenne de chaque département présent dans les données."""
        self.__verifier_colonnes(df, [COL_DEPARTEMENT, COL_CONSO])
        moyennes = df.groupby(COL_DEPARTEMENT, observed=True)[COL_CONSO].mean()
        return pd.DataFrame(
            {f"Conso moyenne ({UNITE_CONSO})": moyennes.values},
            index=[f"{NOMS_DEPARTEMENTS.get(str(c), c)} ({c})" for c in moyennes.index],
        )
