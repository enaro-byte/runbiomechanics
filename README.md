# RunBiomechanics 🏃‍♂️

**Un tableau de bord open source pour explorer ses données de course à pied.**

RunBiomechanics est un projet indépendant en développement. Il permet d'importer un historique de séances, de visualiser la distance et l'allure, d'explorer quelques indicateurs physiologiques disponibles et de comparer l'utilisation de différentes chaussures.

> **État du projet :** première version fonctionnelle (prototype éducatif). L'application n'analyse pas encore la vidéo, les forces au sol ou la cinématique 3D. Elle ne réalise pas de diagnostic médical et ne prouve pas qu'un modèle de chaussure est supérieur à un autre.

## Fonctionnalités

- Tableau de bord : nombre de séances, distance cumulée, allure moyenne et fréquence cardiaque moyenne si disponible.
- Import d'un fichier CSV personnel.
- Graphique de la distance par séance et historique filtrable.
- Exploration de la fréquence cardiaque et de la cadence lorsque ces colonnes existent.
- Comparaison descriptive des chaussures : nombre de séances, kilomètres et allure observée.
- Données de démonstration incluses pour essayer l'application immédiatement.
- Tests automatisés des fonctions de calcul et de préparation des données.

## Aperçu des données acceptées

| Colonne | Obligatoire ? | Description |
|---|---:|---|
| `date` | Oui | Date de la sortie, par exemple `2026-10-01` |
| `distance_km` | Oui | Distance en kilomètres |
| `duration_min` | Oui | Durée totale en minutes |
| `avg_hr_bpm` | Non | Fréquence cardiaque moyenne, en battements/minute |
| `cadence_spm` | Non | Cadence, en pas/minute selon l'appareil |
| `elevation_m` | Non | Dénivelé positif ou valeur d'altitude fournie |
| `shoes` | Non | Nom du modèle de chaussures |
| `surface` | Non | Route, piste, sentier, etc. |

Un exemple est disponible dans [`data/sample_runs.csv`](data/sample_runs.csv). Les données incluses sont fictives.

## Lancer le projet sur son ordinateur

### 1. Installer Python

Installe Python 3.10 ou une version plus récente : <https://www.python.org/downloads/>.

### 2. Télécharger le projet

Sur la page GitHub du dépôt, clique sur **Code**, puis **Download ZIP**, et décompresse l'archive. Tu peux aussi utiliser Git :

```bash
git clone https://github.com/TON-PSEUDO/runbiomechanics.git
cd runbiomechanics
```

Remplace `TON-PSEUDO` par ton identifiant GitHub.

### 3. Créer un environnement virtuel

**Windows (PowerShell)**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Si PowerShell bloque l'activation, ouvre un terminal `cmd` et lance :

```bat
.venv\Scripts\activate.bat
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Installer les dépendances

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Démarrer l'application

```bash
streamlit run app.py
```

Streamlit ouvre normalement l'application dans ton navigateur. Pour arrêter le serveur, reviens au terminal et fais `Ctrl + C`.

## Lancer les tests

Installe les dépendances de développement et lance les tests :

```bash
pip install -r requirements-dev.txt
pytest
```

## Publier le projet sur GitHub (sans utiliser le terminal)

1. Connecte-toi sur <https://github.com/> et crée un dépôt public nommé `runbiomechanics`.
2. Ne coche pas l'ajout automatique d'un README, d'une licence ou d'un `.gitignore` : ils sont déjà présents dans ce dossier.
3. Sur la page du dépôt, choisis **Add file → Upload files**.
4. Dépose le contenu du dossier du projet (les fichiers et dossiers, pas seulement le ZIP).
5. Dans le champ du message, écris `Initial commit: create RunBiomechanics prototype`.
6. Clique sur **Commit changes**.

Une fois le dépôt publié, son adresse sera de la forme :

`https://github.com/TON-PSEUDO/runbiomechanics`

## Feuille de route

- [x] Première application Streamlit et données d'exemple
- [x] Import CSV et nettoyage des données
- [x] Indicateurs simples et graphiques
- [x] Tests unitaires des fonctions principales
- [ ] Ajouter l'import de fichiers GPX
- [ ] Ajouter une analyse de dénivelé et de terrain
- [ ] Ajouter un journal d'usure des chaussures
- [ ] Concevoir un protocole de comparaison de chaussures plus rigoureux
- [ ] Explorer des données de foulée issues de capteurs compatibles

## Principes et limites scientifiques

Une allure, une fréquence cardiaque ou une cadence ne suffisent pas à caractériser à elles seules la biomécanique d'un coureur. Une comparaison valable entre chaussures nécessiterait notamment de contrôler le protocole, le parcours, la vitesse, la fatigue, les conditions environnementales et les caractéristiques des participants. Les évolutions futures devront documenter les méthodes, les limites et les sources des données.

## Contribuer

Les suggestions, signalements de bugs et contributions sont bienvenus. Avant de proposer une analyse, indique les unités utilisées, la provenance des données et les limites connues.

## Licence

Ce projet est distribué sous licence MIT. Voir le fichier [`LICENSE`](LICENSE).
