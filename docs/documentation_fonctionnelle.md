# Documentation fonctionnelle 
Nous avons récupéré les données provenant de deux bases sur l'API de l'ADEME: DPE logement existants: [lien](https://data.ademe.fr/datasets/dpe03existant) et DPE logement neufs [lien](https://data.ademe.fr/datasets/dpe02neuf)
## 1. Intérêt de chaque page
Les pages **lisent les données** à travers des fichiers .parquet : **les statistiques ne sont pas calculées en temps réel**. Les données de l'API sont **téléchargées une fois et stockées sur disque**. Seule la prédiction est calculée à la demande.

- **Accueil** : présentation du projet et des pages que l'utilisateur peut visiter.
- **Contexte** : présentation des données nettoyées, **sans interprétation**. Il est possible de naviguer sur la carte interactive en ajoutant divers filtres. **Les données peuvent être rafraîchies depuis cette page** (mot de passe demandé).
- **Statistiques** : données nettoyées et interprétées à travers plusieurs graphiques. **Par défaut, il n'y a pas de filtre actif** : nous visualisons tous les départements et les deux sources (neufs et existants).
- **Prédiction** : l'utilisateur choisit son département puis remplit un formulaire pour obtenir une prédiction de la consommation de son logement et de son étiquette DPE. La fiabilité du modèle est affichée et une option permet de ré-entraîner le modèle sur les données existantes (mot de passe demandé).

## 2. Fonctionnalités majeures de l'application

Nous avons fait le choix de travailler sur $n$ départements Nous avons fixé $n$ à 3 afin d'avoir matière à comparer sans pour autant dépasser les limites de temps d'exécution et d'espace imposées par *github* et *render*. 
Le diagramme complet de l'application se trouve sur notre [github]().

### Étape par étape
Toutes les étapes sont lancées par une seule commande (`python -m src.orchestration.train`) et **toujours dans le même ordre**. Chaque téléchargement crée un *snapshot*, identifié par sa date et son heure, que l'on retrouve dans tous les dossiers.

**1. Récupération.** Les $n$ départements retenus sont ceux qui présentent **le plus de DPE disponibles** : Paris (75), le Nord (59) et le Rhône (69). Ce classement a été calculé une fois lors de l'exploration et il est lu dans un fichier .csv.
Pour chaque département, nous appelons l'API de l'ADEME sur les deux bases. Le téléchargement est **plafonné à 100 000 lignes par base et par département**. Les données brutes sont stockées dans `data/raw`.

**2. Audit et pré-traitement.** **L'audit contrôle les colonnes** avant le nettoyage : il fait l'état des colonnes par rapport au snapshot précédent.
Le pré-traitement fusionne ensuite les logements neufs et existants de chaque département, puis nettoie : doublons, immeubles entiers, données aberrantes, colonnes vides à plus de 80 %.Le résultat est stocké dans `data/processed`, avec un fichier `meta.json` qui garde le bilan du nettoyage.

**3. Statistiques.** Tous les tableaux affichés par les pages Contexte et Statistiques sont **calculés à cette étape** et stockés dans `data/stats`. C'est ce qui permet aux pages de ne faire que de la lecture.

**4. Entraînement.** Nous entraînons **deux modèles par département** : une classification (DPE) et une régression (consommation).
- Les données sont séparées en 70 % pour l'entraînement et 30 % pour le test. Le découpage est le même pour les deux modèles.
- Les deux modèles héritent d'une même classe (`BaseModel`), ce qui permet au pipeline de les traiter de la même façon.
- Pour l'imputation, **seules les variables qu'un utilisateur peut renseigner dans le formulaire sont utilisées** : les colonnes qui contiennent déjà la réponse (consommations, coûts, émissions) sont écartées.
- Pour la classification, une validation croisée choisit le nombre de variables conservées. 

Chaque modèle est stocké dans `models/` au format joblib, avec un `meta.json` (variables attendues, réglages retenus, métriques).

**5. Prédiction et métriques.** Les modèles sont évalués sur les 30 % de test, et **comparés à une référence naïve** (toujours prédire l'étiquette la plus fréquente, ou la consommation médiane).
- Classification : F1, part d'étiquettes exactes, part d'étiquettes exactes à une classe près, matrice de confusion.
- Régression : R², erreur moyenne (MAE) et RMSE.

Ces tableaux sont stockés avec le modèle : la page Prédiction les lit pour afficher la fiabilité. Une fois l'entraînement terminé, la nouvelle version est **publiée** (`data/snapshot_actif.json`) et les anciennes versions sont supprimées.

**6. Allègement des données.** Avant le déploiement, nous ne gardons que le snapshot et les modèles publiés, et nous réduisons les données nettoyées **aux seules colonnes utilisées par les modèles**. Sans cela, l'application dépasse les 512 Mo de mémoire du plan gratuit de *render*.

**7. Déploiement.**
- **Docker** : une seule image contient le code, les données préparées et les modèles.
- **Render** : héberge l'image et rend l'application accessible en ligne.
- **Github workflow** : le rafraîchissement (page Contexte) et le ré-entraînement (page Prédiction) ne tournent pas dans l'application. Ils lancent, après saisie d'un mot de passe, un workflow qui exécute le pipeline, allège les données et enregistre le résultat sur le dépôt.