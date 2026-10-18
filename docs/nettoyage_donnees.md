# Nettoyage et préparation des données DPE

Ce document explique, de bout en bout, ce qui a été fait sur les données avant l'analyse et la modélisation : **quelles données utiliser, où les trouver, pourquoi elles sont faites ainsi, et comment les rafraîchir** quand un nouveau snapshot arrive.
Il est écrit pour que chacun, sans avoir suivi le travail de nettoyage, puisse comprendre les choix et les remettre en cause s'il le faut.

Pour le détail technique : le code est dans `src/preprocessing.py` (nettoyage), `src/features.py` (préparation pour les modèles) et `src/audit_colonnes.py` (détection des nouvelles colonnes).
Les décisions sont argumentées dans `notebooks/02_nettoyage_donnees.ipynb`, colonne par colonne dans `docs/colonnes_retenues.csv`, et les lignes retirées par règle dans `docs/bilan_nettoyage.csv`.

---

## 1. Vue d'ensemble

Les données viennent de l'API de l'ADEME (DPE des logements existants et neufs). Elles passent par trois étapes, chacune écrite dans un dossier :

```
data/raw/<snapshot>/        données brutes de l'API (224 colonnes, telles que reçues)
        │   nettoyage  (src/preprocessing.py)
        ▼
data/processed/<snapshot>/  données propres et lisibles, 31 colonnes, un fichier par département   ← ANALYSE
        │   encodage   (src/features.py)
        ▼
data/ready/<snapshot>/      données chiffrées, découpées en entraînement / test                    ← MODÈLES
```

Un **snapshot** est une photo des données à un moment donné (il porte la date de son téléchargement). Le snapshot de référence est **`2026-10-12_132605`** : trois départements (59, 69, 75), 393 952 lignes brutes, **386 450 logements après nettoyage** (7 502 retirés, soit 1,9 %).

Ce qu'il faut retenir :
- Si vous faites de l'**analyse ou de la visualisation**, prenez `data/processed`.
- Si vous faites des **modèles**, prenez `data/ready`.
- Les deux contiennent exactement les mêmes logements. Aucune valeur manquante dans l'un comme dans l'autre.

---

## 2. Où trouver les données et comment les ouvrir

### Pour l'analyse et la visualisation
Chemin : `data/processed/2026-10-12_132605/59.parquet`, `69.parquet`, `75.parquet` (un fichier par département).

```python
import pandas as pd
df = pd.read_parquet("data/processed/2026-10-12_132605/59.parquet")
```

Les valeurs sont lisibles (« Gaz naturel », « avant 1948 », « maison ») : c'est ce qui permet de faire des graphiques, des tableaux et des filtres parlants dans Streamlit.
Pour avoir les trois départements ensemble : `pd.concat([...], ignore_index=True)`.

### Pour les modèles
Chemin : `data/ready/2026-10-12_132605/` (contient `X_train` / `X_test` encodés, `X_train_brut` / `X_test_brut` non encodés, `y_train_classe`, `y_test_classe`, `y_train_conso`, `y_test_conso`, `origine_test`, `preprocesseur.joblib`, `meta.json`).

```python
from src.features import charger_jeu
jeu = charger_jeu()        # prend le snapshot le plus récent de data/ready/
```

- Classification (étiquette DPE de A à G) : `jeu["X_train"]`, `jeu["y_train_classe"]` pour entraîner ; `jeu["X_test"]`, `jeu["y_test_classe"]` pour évaluer.
- Régression (consommation en kWh/m²/an) : `jeu["y_train_conso"]` et `jeu["y_test_conso"]`.
- `jeu["X_train_brut"]` et `jeu["X_test_brut"]` sont les **mêmes logements avant encodage** (12 colonnes lisibles) : à utiliser pour construire le modèle final (voir section 5).
- `jeu["origine_test"]` dit si chaque logement de test est « dpe_existants » ou « dpe_neufs » : utile pour évaluer le modèle sur les existants seuls (les neufs sont presque tous en A, B ou C).
- `jeu["preprocesseur"]` est la « recette » de transformation (voir plus bas) : l'application l'utilisera pour transformer la saisie d'un utilisateur de la même manière.

### Que contient `data/ready/<snapshot>/` ? (11 fichiers)
| Fichier | Contenu |
|---|---|
| `X_train`, `X_test` | variables d'entrée **encodées** : 30 colonnes, uniquement des nombres |
| `X_train_brut`, `X_test_brut` | **les mêmes logements avant encodage** : 12 colonnes lisibles (surface, hauteur, période, type de bâtiment, énergie, installations, 4 qualités d'isolation, origine) |
| `y_train_classe`, `y_test_classe` | l'étiquette DPE à prédire (A à G) |
| `y_train_conso`, `y_test_conso` | la consommation à prédire (kWh/m²/an) |
| `origine_test` | « dpe_existants » ou « dpe_neufs » pour chaque logement de test |
| `preprocesseur.joblib` | la « recette » d'encodage apprise sur l'entraînement (voir section 5) |
| `meta.json` | snapshot utilisé, date de création, nombre de lignes, liste des 30 colonnes, cibles |

**Pourquoi 12 colonnes deviennent 30.** Les 12 colonnes de `X_*_brut` ne sont pas toutes traitées de la même façon :
- 2 numériques (surface, hauteur) restent telles quelles ;
- 4 ordonnées (période de construction et 3 qualités d'isolation) deviennent un rang chacune : 4 colonnes ;
- 6 sans ordre (type de bâtiment, énergie, installation de chauffage, installation d'eau chaude, plancher bas, origine) sont éclatées en **une colonne 0/1 par modalité** : 24 colonnes.
Soit 2 + 4 + 24 = 30. Dans `X_train`, les noms de colonnes portent un préfixe qui indique le traitement (`num__`, `ord__`, `nom__`).
Les lignes de `X_*`, `X_*_brut` et `y_*` sont **alignées par leur ordre** : la ligne n de chaque fichier décrit le même logement.

**Lequel choisir ?** `X_train` / `X_test` pour comparer rapidement des modèles ; `X_train_brut` / `X_test_brut` pour le modèle final, enregistré sous forme de pipeline complet (section 5).

Chiffres : 309 160 logements d'entraînement, 77 290 de test (80 % / 20 %), 30 colonnes, toutes numériques, aucune valeur manquante.
Si les fichiers manquent ou sont à jour, on les régénère avec `python -m src.features`.

---

## 3. Pourquoi deux jeux de données, et pourquoi toutes les colonnes ne servent pas aux deux

L'analyse et la modélisation n'ont pas les mêmes besoins.

**L'analyse** doit pouvoir lire et comparer : elle a besoin de valeurs en clair, de la géographie (communes, cartes), et de toutes les informations utiles pour comprendre les logements, y compris les résultats du calcul du DPE (consommation par usage, coût, émissions de gaz à effet de serre).

**Un modèle** a pour rôle de **prédire** la classe DPE et la consommation d'un logement **à partir de ses caractéristiques**, c'est-à-dire de ce qu'une personne connaît ou peut saisir dans l'application. Il a donc des contraintes que l'analyse n'a pas.

### Colonnes utilisées en analyse mais jamais en entrée d'un modèle
- **Les 9 colonnes « analyse seule »** : `etiquette_ges`, `emission_ges_5_usages_par_m2`, `conso_5_usages_ep`, `conso_chauffage_ep`, `conso_ecs_ep`, `conso_eclairage_ep`, `conso_auxiliaires_ep`, `cout_total_5_usages`, `ubat_w_par_m2_k`.
  Ce sont des **résultats du calcul du DPE**. L'étiquette DPE et la consommation par m² sont calculées *à partir d'elles* : les donner au modèle, c'est lui donner la réponse. Il aurait un excellent score, mais ne servirait à rien en vrai, puisque l'utilisateur ne connaît pas ces valeurs avant d'avoir fait le diagnostic. On parle de **fuite de données**. Elles restent précieuses pour l'analyse (comprendre d'où vient la consommation, comparer les coûts).
- **Les identifiants et la date** (`numero_dpe`, `date_reception_dpe`) : ils n'ont aucun pouvoir explicatif sur la consommation et ne seraient pas connus lors d'une prédiction.
- **La géographie en texte** (code postal, commune, code INSEE, département) et **la latitude / la longitude** : utiles pour les cartes et les comparaisons entre territoires. Exclues des modèles parce qu'un utilisateur ne connaît pas ses coordonnées, et que la période de construction et le type de bâtiment portent déjà en grande partie l'information sur le type de quartier. **Cette décision est à valider par l'équipe modèles** (voir les questions ouvertes).
- **Les deux cibles** (`etiquette_dpe`, `conso_5_usages_par_m2_ep`) : elles sont à prédire, donc évidemment pas en entrée.

### Colonnes d'entrée du modèle
Surface, hauteur sous plafond, période de construction, type de bâtiment, énergie de chauffage, type d'installation de chauffage et d'eau chaude, qualité d'isolation (enveloppe, murs, menuiseries, plancher bas), et l'origine (neuf ou existant).
Toutes sont aussi disponibles en analyse : **ce qui entre dans un modèle est toujours un sous-ensemble de ce qui sert à l'analyse, jamais l'inverse.**
La seule différence est la forme : dans `data/ready`, ces colonnes sont transformées en nombres (voir section 5).

### Tableau récapitulatif (31 colonnes de `data/processed`)
| Colonne | Analyse | Modèle | Remarque |
|---|---|---|---|
| `etiquette_dpe` | oui | **cible** (classification) | A à G |
| `conso_5_usages_par_m2_ep` | oui | **cible** (régression) | kWh/m²/an, énergie primaire |
| `surface_habitable_logement` | oui | entrée | m², entre 5 et 500 |
| `periode_construction` | oui | entrée | 10 périodes ordonnées |
| `type_batiment` | oui | entrée | maison ou appartement (immeubles exclus) |
| `hauteur_sous_plafond` | oui | entrée | m, entre 1,8 et 5 |
| `type_energie_principale_chauffage` | oui | entrée | énergies rares regroupées |
| `type_installation_chauffage`, `type_installation_ecs` | oui | entrée | « non applicable » si vide |
| `qualite_isolation_enveloppe`, `_murs`, `_menuiseries`, `_plancher_bas` | oui | entrée | échelle de 4 niveaux ; plancher bas peut valoir « non applicable » |
| `origine` | oui (filtre) | entrée | dpe_existants ou dpe_neufs |
| `latitude`, `longitude` | oui (cartes) | non | décision à valider |
| `code_departement_ban`, `code_postal_ban`, `nom_commune_ban`, `code_insee_ban` | oui | non | géographie |
| `numero_dpe`, `date_reception_dpe` | oui | non | identification |
| 9 colonnes « analyse seule » (liste ci-dessus) | oui | **jamais** | contiennent la réponse |

Le sens des colonnes est déduit de leur nom : à confirmer dans le dictionnaire de données de l'ADEME.

---

## 4. Le nettoyage, règle par règle

Le code est dans `src/preprocessing.py`. Une fonction par règle, et tous les seuils sont des constantes en haut du fichier : pour changer un seuil, un seul endroit à modifier.
Le nettoyage s'applique **séparément à chaque département**, après fusion des logements existants et neufs (la colonne `origine` garde la trace de la provenance).
Il se lance avec `python -m src.train --snapshot <id> --preprocess`.

### 4.1 Choisir les colonnes : de 224 à 30 (31 avec la géographie transformée)
L'API fournit 224 colonnes. On en garde **30** (liste blanche dans `COLONNES_GARDEES`) : 21 utiles à la fois pour l'analyse et pour les modèles, et les 9 « analyse seule ».
Les 194 autres sont écartées parce qu'elles sont (d'après les notes du notebook) : techniques, des adresses détaillées, des résultats intermédiaires du calcul du DPE, des équipements très détaillés, trop incomplètes (de 46 % à 100 % de manquants selon le type de logement), redondantes (`annee_construction`, `version_dpe`, dates secondaires) ou incohérentes (`nombre_niveau_logement`, `type_energie_principale_ecs`).
La décision pour chaque colonne et sa raison sont dans `docs/colonnes_retenues.csv`.
Pourquoi une liste blanche (on liste ce qu'on garde) plutôt qu'une liste noire ? Parce que si l'API ajoute demain une colonne, elle est ignorée par défaut au lieu de se glisser sans contrôle dans les données (voir section 6).
La colonne `_geopoint` (« latitude,longitude » en un seul texte) est transformée en deux colonnes numériques, `latitude` et `longitude`, d'où 31 colonnes en sortie.

### 4.2 Les règles qui retirent des lignes
Sur le snapshot `2026-10-12_132605` :

| Règle | Critère | Pourquoi | Lignes retirées (59 / 69 / 75) |
|---|---|---|---|
| Doublons | un seul DPE par `numero_dpe` | un même diagnostic ne doit pas compter deux fois | 0 |
| Immeubles | on retire `type_batiment = immeuble` | un DPE d'immeuble décrit un bâtiment entier, pas un logement : il fausserait les moyennes par logement | 1 245 / 1 895 / 990 |
| Manquants clés | numéro, étiquette, consommation ou surface absents | sans eux, la ligne est inutilisable pour les deux objectifs | 210 / 306 / 192 |
| Étiquettes | on garde A à G | toute autre valeur est une erreur | 0 |
| Surface | entre **5 et 500 m²** | en dessous, ce n'est pas un logement ; au-dessus, ce sont surtout des erreurs de saisie | 56 / 37 / 77 |
| Consommation | **supérieure à 0 et au plus 1 000 kWh/m²/an** | au-delà, valeurs extrêmes isolées, très probablement des erreurs de calcul ou de saisie ; le seuil est large pour ne retirer que l'aberrant | 26 / 21 / 150 |
| Émissions de GES | au plus **1 000 kg CO₂/m²/an** | des émissions impossibles (jusqu'à 5 900 observées à Lyon, avec une étiquette G fausse) | 0 / 30 / 0 |
| Filet de sécurité | toute ligne qui a encore une valeur manquante | garantir des fichiers sans trou (voir 4.4) | 851 / 1 093 / 323 |

**Pourquoi le seuil de surface est à 5 m² et non 9 m².** Le seuil de 9 m² (surface minimale d'un logement à la location) retirait à Paris 1 169 logements. On a regardé leurs surfaces : aucune à zéro, une seule entre 1 et 3 m², 53 entre 3 et 5, 288 entre 5 et 7 et 797 entre 7 et 9. Ce sont de vrais petits logements (chambres de bonne, petits studios), pas des erreurs. Les retirer aurait mal représenté Paris et privé le modèle de ces cas. Passer à 5 m² en récupère environ 1 050 et garde l'exclusion des valeurs absurdes.

Les autres seuils (500 m², 1 000 kWh/m²/an, 1 000 kg CO₂/m²/an) viennent d'un examen des valeurs extrêmes dans le notebook ; ce sont des seuils larges, qui ne retirent que de rares lignes (de 0 à 150 par département). Ils devraient être revérifiés à chaque grosse mise à jour (voir section 6), et la sensibilité au seuil de consommation (1 000 contre 800) reste à étudier.

### 4.3 Les règles qui gardent la ligne en corrigeant la valeur
On préfère corriger plutôt que supprimer quand la ligne reste utile.
- **Coordonnées hors de la France métropolitaine** (latitude hors de 41-52, longitude hors de -5,5-10) : remplacées par « manquant ». Dans les données de l'ADEME, une position erronée est commune à plusieurs logements de Lille et de Lyon. La ligne reste utile pour la consommation, mais ne peut pas s'afficher sur une carte.
- **Hauteur sous plafond hors de 1,8-5 m** : remplacée par « manquant » (souvent une saisie en centimètres).
- **Énergies de chauffage rares regroupées** : « Bois » (toutes les variantes), « Autre » (les modalités très rares), « Non affecté » et « Inconnu » gardées à part. Une modalité portée par quelques logements n'apporte rien à un modèle.
- **Installation de chauffage ou d'eau chaude manquante → « non applicable »** : ce n'est pas un oubli, la colonne est vide pour les maisons (installation individuelle).
- **Qualité d'isolation du plancher bas manquante → « non applicable »** : 9,1 % à Paris, uniquement pour les logements existants (jamais manquant dans les neufs, ce qui suggère un effet de la méthode de calcul). On ne sait pas distinguer un manque structurel (pas de plancher donnant sur l'extérieur) d'un oubli du diagnostiqueur. Dans les deux cas, on **n'invente pas un niveau d'isolation** : la modalité est conservée à part, et le modèle peut apprendre ce qu'elle signifie.
- **Espaces superflus supprimés** dans les textes.

### 4.4 Le filet de sécurité
Après toutes ces règles, il peut rester quelques valeurs manquantes (coordonnées erronées, hauteur absente). Pour que les fichiers sortent **toujours sans aucun trou**, la dernière étape supprime les lignes encore incomplètes : 2 267 logements (0,6 %) sur ce snapshot.
Cette perte est visible dans le bilan. Si une future mise à jour fait apparaître un manque inattendu dans une colonne, cette étape l'attrape aussi, et on voit tout de suite la perte.
Une colonne entièrement vide pour un département ne supprime pas toutes les lignes : l'étape prévient par un avertissement.
Inconvénient assumé : on retire quelques logements valables pour la consommation à cause d'une coordonnée erronée. C'est le prix de fichiers sans trou, à un coût inférieur à 1 %.

---

## 5. La préparation pour les modèles (`src/features.py`)

Un modèle ne comprend que des nombres. `features.py` transforme les colonnes de `data/processed` en `data/ready`.

### Ce qu'il fait
1. **Il met de côté les colonnes interdites** (cibles, colonnes qui contiennent la réponse, identifiants, géographie).
2. **Il découpe en entraînement (80 %) et test (20 %)**, de façon *stratifiée* : la proportion de chaque étiquette A à G est la même dans les deux parties, ce qui compte pour les classes rares.
3. **Il apprend les règles de transformation sur l'entraînement seulement**, puis les applique à l'entraînement et au test.
4. **Il encode** :
   - *colonnes ordonnées* (période de construction, qualités d'isolation) : remplacées par un rang (par exemple insuffisante = 0, moyenne = 1, bonne = 2, très bonne = 3), parce que l'ordre a un sens ;
   - *colonnes sans ordre* (type de bâtiment, énergie, installations, plancher bas, origine) : une colonne 0/1 par modalité (« one-hot »), parce qu'aucune modalité n'est « plus grande » qu'une autre ;
   - *nombres* (surface, hauteur) : conservés tels quels.
5. **Il remplit les manquants** (médiane pour les nombres, « Inconnu » pour les textes). Il n'y en a plus dans les fichiers actuels, mais c'est une protection pour l'application : un utilisateur peut laisser un champ vide.

### Deux façons de s'en servir
- **Pour explorer et comparer des modèles rapidement** : prendre `X_train` / `X_test`, déjà encodés (`charger_jeu()`).
- **Pour le modèle final** : l'architecture du projet prévoit que `classifier.joblib` et `regressor.joblib` soient des **pipelines complets** (prétraitement + estimateur dans un seul objet), pour que l'application puisse leur envoyer directement la saisie brute d'un utilisateur. On part alors des données **non encodées** :
  ```python
  from sklearn.pipeline import Pipeline
  from sklearn.ensemble import RandomForestClassifier
  from src.features import charger_jeu, construire_preprocesseur

  jeu = charger_jeu()
  modele = Pipeline([("prep", construire_preprocesseur()),
                     ("modele", RandomForestClassifier(class_weight="balanced"))])
  modele.fit(jeu["X_train_brut"], jeu["y_train_classe"])
  modele.predict(jeu["X_test_brut"].head(1))   # accepte une saisie brute, même avec un champ vide
  ```
  Le préprocesseur est alors appris dans `fit`, sur l'entraînement seulement. La liste des colonnes d'entrée à enregistrer dans `metadata.json` est `FEATURES` (dans `src/features.py`).

### Pourquoi apprendre sur l'entraînement seulement
Si les règles (la médiane, la liste des modalités) étaient calculées sur toutes les données, y compris le test, le modèle « verrait » un peu du test avant d'être évalué, et ses scores seraient trop beaux. On évite cette **fuite de données** en apprenant tout sur l'entraînement.

### Le fichier `preprocesseur.joblib`
`joblib` est la bibliothèque qui permet d'enregistrer un objet Python dans un fichier. Ici, le fichier contient la « recette » apprise : l'ordre des périodes, la liste des modalités, les valeurs de remplissage.
L'application Streamlit le rechargera pour transformer la saisie d'un utilisateur exactement comme les données d'entraînement. Sans lui, le modèle recevrait des nombres qui ne correspondent pas à ce qu'il a appris.
Il dépend de la version de scikit-learn : c'est pour cela que `requirements.txt` fixe les versions.

### Les classes sont déséquilibrées
Répartition des étiquettes (entraînement) : C 32,8 % · D 25,4 % · E 18,1 % · F 7,5 % · B 6,3 % · G 5,0 % · A 4,9 %.
Un modèle qui répondrait toujours « C » aurait déjà environ 33 % de bonnes réponses sans rien comprendre. Il ne faut donc pas juger sur la seule exactitude : utiliser le **F1 macro**, la **matrice de confusion**, la pondération des classes (`class_weight="balanced"`), et évaluer aussi sur les existants seuls.

---

## 6. Guide : rafraîchir les données avec un nouveau snapshot

À faire à chaque fois qu'un nouveau snapshot est disponible dans `data/raw/<id>/`.

### Étape 1 : obtenir le snapshot
```
python -m src.refresh
```
Cette commande interroge l'API de l'ADEME et ne télécharge que si l'ADEME a publié une version plus récente que le dernier snapshot (le téléchargement se fait page par page). Elle écrit `data/raw/<id>/` (un sous-dossier par département). On peut aussi l'obtenir avec `python -m src.train --refresh`.
À confirmer : `train.py` appelle `refresh(size=10000)` en dur ; est-ce une taille de page ou un plafond du nombre de lignes ? Le plafond de 100 000 existants par département du snapshot actuel doit être documenté ici.
Attention : cette commande lance un vrai téléchargement (`--help` ne l'en empêche pas).

### Étape 2 : auditer les colonnes (à ne pas sauter)
```
python -m src.audit_colonnes
```
(ou `--snapshot <id>`). L'outil compare les colonnes du snapshot à celles déjà examinées dans `docs/colonnes_retenues.csv` et affiche :
- **Colonnes disparues** : doit afficher *aucune*. Sinon, corriger `preprocessing.py` avant de continuer (le nettoyage s'arrête de toute façon si une colonne critique manque).
- **Colonnes nouvelles**, avec le taux de manquants, des exemples de valeurs et une suggestion. `ÉCARTER` : famille qui contient la réponse (`conso_`, `cout_`, `emission_ges`…), identifiant, trop vide, constante ou trop de modalités. `CANDIDATE` : à examiner (utile pour prédire ? saisissable dans l'application ?).
- Pour garder une colonne : l'ajouter à `COLONNES_GARDEES` dans `preprocessing.py`, et dans `features.py` si c'est une entrée de modèle.
- Dans tous les cas, **noter la décision** dans `docs/colonnes_retenues.csv` (gardée ou supprimée), pour que l'audit suivant ne la signale plus.

L'outil propose, ce sont des humains qui décident : une règle automatique ne peut pas savoir si une colonne bien remplie contient en réalité la réponse.
Sur le snapshot actuel, l'audit a trouvé 9 colonnes nouvelles, toutes vides à 100 % (détail rare d'un deuxième générateur d'eau chaude) : aucune n'est utile, elles sont notées comme supprimées.

### Étape 3 : nettoyer
```
python -m src.train --snapshot <id> --preprocess
```

### Étape 4 : contrôler le bilan
Afficher le nombre de lignes restantes après chaque règle, pour chaque département :
```
python -c "from src.data.repository import DataRepository as R; from src.preprocessing import DataPreprocessor as P; r=R(); p=P(); p.process(r.load('<id>')); [print(d, chr(10), p.bilans[d].to_string()) for d in p.bilans]"
```
Ce qu'on cherche : le total retiré reste de l'ordre de 2 % ; aucune règle ne retire soudain beaucoup plus que d'habitude. Une règle qui s'emballe (par exemple la surface à Paris avec l'ancien seuil) est le signe qu'un seuil n'est plus adapté à ces données. C'est comme cela que le seuil de 9 m² a été corrigé.
(`docs/bilan_nettoyage.csv` est écrit par le notebook ; `train.py` n'enregistre pas le bilan.)

### Étape 5 : vérifier l'absence de valeur manquante
```
python -c "import pandas as pd; d=pd.read_parquet('data/processed/<id>/75.parquet'); print(int(d.isna().sum().sum()))"
```
(pour chaque département). Le résultat doit être 0.

### Étape 6 : générer le jeu des modèles (seulement si on réentraîne)
```
python -m src.train --snapshot <id> --features
```
(ou `python -m src.features --snapshot <id>`, équivalent). Écrit `data/ready/<id>/` à partir de `data/processed/<id>/` : le nettoyage doit donc avoir été fait avant. Sans aucune option, `python -m src.train` enchaîne maintenant les trois étapes : chargement, nettoyage, jeu des modèles.
D'après l'architecture du projet, les modèles ne sont **pas** réentraînés à chaque rafraîchissement des données : l'entraînement est manuel, environ une fois par an ou après un changement de méthode du DPE. Un rafraîchissement met à jour les données de l'application ; cette étape n'est nécessaire que pour réentraîner.
```
python -m src.features --snapshot <id>
```
Écrit `data/ready/<id>/`. Vérifier : `python -c "from src.features import charger_jeu; j=charger_jeu(); print(j['X_train'].shape)"`.

### Étape 7 : documenter et enregistrer
Mettre à jour ce document si une décision a changé, puis enregistrer (commit).

### Ce qui est automatique et ce qui ne l'est pas
| Situation | Pris en charge ? |
|---|---|
| Règles de nettoyage, filet de sécurité | oui, par l'étape `preprocess` |
| Colonne critique disparue | oui : arrêt avec un message clair |
| Colonne secondaire disparue | oui : recréée vide, avertissement |
| Nouvelle colonne de l'API | ignorée sans erreur ; **détectée seulement par l'audit (étape 2, à lancer à la main)** |
| Nouvelle valeur (période, niveau d'isolation) | avertissement ; encodée « inconnue » sans plantage |
| Seuils adaptés aux nouvelles données | **non** : à vérifier avec le bilan (étape 4) |
| Jeu pour les modèles (`data/ready`) | oui si on lance `train.py` sans option ou avec `--features` (étape `features`) ; `python -m src.features` reste possible seul |
| Doublons entre ancien et nouveau snapshot | **non** : la déduplication ne travaille que sur un snapshot |
| Rafraîchissement lancé depuis l'application | télécharge un snapshot brut ; le **nettoyage doit être appelé ensuite** (`DataPreprocessor().process(...)` puis `save_processed`), et l'audit des colonnes aussi : à brancher dans `AppService` |

---

## 7. Limites des données (à reprendre dans le rapport)
- **Échantillon plafonné** : 100 000 logements existants par département (plafond atteint dans les trois). Les logements neufs (8 644 à Paris, 40 344 dans le Nord, 44 964 dans le Rhône) sont sous le plafond, donc probablement complets. Le poids des neufs varie beaucoup : environ 8 % à Paris contre 29 à 31 % ailleurs.
- **Pas forcément un tirage aléatoire.** Sur l'ancien snapshot de 10 000 lignes, les existants de Lille et Lyon étaient concentrés sur 2021 et 2026, ceux de Paris sur 2026. À revérifier sur le snapshot de 100 000 lignes avant toute conclusion sur l'évolution dans le temps.
- **Trois départements seulement** : les modèles ne sont fiables que pour des logements comparables.
- Les neufs classés « immeuble » sont exclus, même ceux qui décrivent un logement isolé.
- Environ 0,6 % des logements sont retirés à cause d'une position GPS erronée ou d'une hauteur absente, alors que leur consommation est valable.
- Ne pas additionner les consommations par usage : sur l'ancien snapshot, leur somme dépassait la consommation totale pour 51 % des lignes (cause non élucidée, à vérifier dans le dictionnaire de l'ADEME).
- Pour les KPI et les graphiques, préférer la **médiane** (robuste aux valeurs extrêmes) et la consommation **par m²**. Présenter les chiffres comme ceux de l'échantillon, pas du parc réel.

## 8. Questions ouvertes
- L'échantillon des existants est-il un tirage aléatoire ? (la colonne `_rand` de l'API permettrait d'en tirer un.)
- Que signifie `size=10000` dans `refresh()` (taille de page ou plafond) ? Comment obtenir un snapshot de 100 000 lignes par département ?
- Qui appelle le nettoyage après un rafraîchissement lancé depuis l'application ? Et comment l'avertissement de colonnes absentes (`check_compatibility`) se combine-t-il avec le contrôle de `preprocessing.py` ?
- Le diagramme de classes attribue le découpage entraînement / test à `DataPreprocessor` ; il est fait dans `src/features.py`. Mettre le diagramme à jour (ou déplacer le code).
- Sensibilité au seuil de consommation : refaire l'étude avec 800 au lieu de 1 000.
- Localisation dans les modèles : rien (choix actuel), le département, ou latitude / longitude. À trancher en comparant les scores avec et sans.
- L'étape `features` a été ajoutée à `train.py` (modification minimale, à relire). Reste à retirer le bloc de démonstration (« A SUPPRIMER ») et les commentaires TODO devenus obsolètes.

## 9. Mini-glossaire
- **Snapshot** : photo des données de l'API à un moment donné, stockée dans un dossier daté.
- **Parquet** : format de fichier de tableau, compact et rapide (on s'en sert à la place du CSV).
- **Encodage** : transformer du texte (« Gaz naturel ») en nombres que le modèle comprend.
- **Fuite de données** : donner au modèle, sans le vouloir, la réponse ou une information du jeu de test. Résultat : des scores trop beaux et un modèle inutilisable en vrai.
- **Pipeline** : suite d'étapes de transformation enchaînées, apprises une fois puis réutilisées à l'identique.
- **joblib** : bibliothèque qui enregistre un objet Python (ici la recette d'encodage) dans un fichier.
