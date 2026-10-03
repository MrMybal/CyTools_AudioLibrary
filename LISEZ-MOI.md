# CyTools_AudioLibrary

Bibliothèque audio locale intelligente : gestion, analyse, catégorisation et recherche en langage
naturel dans de grandes collections de sons. Vos fichiers ne sont jamais déplacés, copiés ni modifiés
(sauf si vous utilisez vous-même l'onglet *Outils fichiers*, voir plus bas) :
une bibliothèque *référence* des dossiers, et tout ce que le Tool calcule (base, waveforms, embeddings,
index) va dans un cache que vous placez où vous voulez.

## Démarrer

0. **Depuis une release GitHub** : téléchargez `CyTools_AudioLibrary-<version>-windows-x64.zip`, décompressez-le
   là où l'application doit vivre (elle crée son environnement privé dans ce dossier), puis, une seule fois,
   ouvrez PowerShell dans le dossier décompressé et lancez :
   `powershell -ExecutionPolicy Bypass -File app\Install.ps1`
   Il faut Python 3.11 ou plus récent et git. Les deux autres fichiers de la release (`cytools-app.zip` et
   son `.sha256`) servent à l'onglet *Mises à jour* : ne les décompressez pas à la main.
1. Double-cliquez sur **CyTools_AudioLibrary.exe** (Linux : `./CyTools_AudioLibrary.sh`, non testé).
   Si un message indique que le runtime privé est absent, c'est que l'étape 0 n'a pas été faite.
2. Onglet **Installation** : installez le *moteur IA* (PyTorch privé, plusieurs Go), puis les modèles
   voulus. L'assistant de recherche *CySearchAssist-CLAP-1.5B* (1,6 Go, par défaut) ou sa version
   *0.5B* (0,5 Go, plus légère) vient de Hugging Face, comme dans CyMetaSound. Pour un modèle dont la licence l'exige, lisez-la et cochez vous-même la case d'acceptation :
   le Tool ne l'accepte jamais à votre place.
3. Onglet **Bibliothèque** : *Nouvelle bibliothèque* (nom + dossier du cache, par ex.
   `G:\CyToolsCache\AudioLibrary`), *Ajouter un dossier* autant de fois que nécessaire, *Tout rescanner*.
4. Cochez les modèles à utiliser (panneau *Modèles*), puis *Analyser la bibliothèque*. L'onglet
   **File d'analyse** montre l'avancement et permet Pause / Reprendre / Annuler / Réessayer les échecs.
5. Recherchez en langage naturel, dans n'importe quelle langue : « gros impact métallique très lourd
   avec une longue réverbération ». Cliquez un résultat : waveform, lecture immédiate, tête de lecture,
   informations, tags, catégories, score de chaque modèle et segment correspondant.

## Vos tags, catégories et notes, sur un son, une sélection ou un dossier

* **Un son** : onglet *Tags et catégories* sous la waveform. Ajoutez ou retirez vos tags, choisissez une catégorie
  puis *Ajouter la catégorie* ou *Retirer la catégorie*, une note de 0 à 5, une description d'une ligne et des notes libres. Description et notes
  s'enregistrent seules, sans bouton.
* **Plusieurs sons** : Ctrl+clic pour ajouter un son à la sélection, Maj+clic pour prendre toute une plage, Ctrl+A pour
  toute la liste, Échap pour vider. L'onglet devient *Sélection (N)* et chaque modification s'applique à tous : tags
  (chaque tag déjà présent affiche combien de sons le portent, et se retire de tous d'un clic), catégorie, note,
  favori, une ligne ajoutée aux notes de chacun sans effacer l'existant, et *Analyser ces sons*.
* **Un dossier** : panneau gauche, la flèche d'un dossier ouvre ses sous-dossiers avec leur nombre de sons. Un clic
  affiche ce dossier et tout ce qu'il contient ; clic droit : *Sélectionner tous les sons de ce dossier*, *Analyser ce
  dossier*, *Ouvrir le dossier*. Sur un son de la liste, clic droit > *Afficher seulement ce dossier*.

Tout cela reste dans la base de la bibliothèque : vos fichiers audio ne sont pas modifiés. Pour renommer ou écrire les
tags dans les fichiers eux-mêmes, onglet *Outils fichiers*, choix *Les sons sélectionnés*.

## Sortir des sons de la bibliothèque : bundle et glisser-déposer

* **Créer un bundle** : onglet *Sélection* ou clic droit sur un son, *Créer un bundle…*, puis choisissez un dossier. Les
  sons y sont **copiés**, à plat ou en gardant leurs dossiers. Les originaux ne sont ni déplacés ni modifiés, et rien
  n'est écrasé : un fichier identique déjà présent est laissé tel quel, un fichier différent du même nom reçoit un
  nom numéroté. `bundle.json` liste chaque fichier avec sa source, ses tags et ses catégories ; refaire un bundle dans
  le même dossier le complète. Décochez `bundle.json` si vous importez ensuite tout le dossier dans un moteur de jeu.
  Un dossier situé dans une de vos bibliothèques ou dans un cache est refusé : les copies y seraient indexées.
* **Glisser-déposer** : faites glisser un son, ou la sélection, hors de la fenêtre, vers l'Explorateur pour en faire
  des copies, ou vers le *Content Browser* d'Unreal Engine pour les importer dans le projet. Seule la copie est
  proposée : un glisser ne peut jamais déplacer ni effacer vos originaux.

## Mise à jour automatique des bibliothèques

Par défaut, l'application vérifie en arrière-plan (au démarrage puis toutes les 5 minutes) si des fichiers ont été
ajoutés, modifiés ou retirés dans vos dossiers, et met la bibliothèque à jour toute seule, y compris l'analyse IA des
nouveaux sons. Panneau gauche > *Mise à jour automatique* : *Mettre à jour automatiquement*, *Me demander d'abord*
(un bandeau apparaît avec un bouton *Mettre à jour maintenant*) ou *Désactivée*. Les fichiers disparus sont masqués,
jamais supprimés de la base : s'ils reviennent ou ont été déplacés, ils retrouvent leurs tags.

## Utilisation par une IA (MCP)

Une IA connectée au Tool peut chercher un son dans toutes vos bibliothèques (« trouve-moi une grosse porte métallique »)
et vous proposer des fichiers avec leur chemin, et, si vous le lui demandez, créer une bibliothèque, ajouter un dossier,
relancer un scan ou une analyse. Elle peut aussi parcourir l'arborescence de vos dossiers et traiter un dossier entier
en une fois : ajouter des tags, une catégorie ou une ligne de notes à tous ses sons. Configuration : `app/README.md`.

## Outils fichiers (modifient vos fichiers, uniquement à votre demande)

* **Renommer les fichiers mal nommés** (`sound_01`, `ZOOM0012`...) : le Tool propose un nom à partir de la catégorie et
  des tags ; vous cochez, corrigez si besoin, confirmez. Rien n'est écrasé, *Annuler le dernier renommage* existe, et
  les tags et analyses suivent le fichier.
* **Écrire les tags dans les fichiers** (l'équivalent audio de l'EXIF : ID3, Vorbis, MP4) pour que d'autres logiciels
  les lisent. L'audio est vérifié identique avant de remplacer l'original, et une sauvegarde est gardée dans le cache.

## Raccourcis

Espace : lecture/pause · Haut/Bas : son précédent/suivant (Maj+Haut/Bas étend la sélection) · Ctrl+clic, Maj+clic,
Ctrl+A : sélection multiple · Échap : vider la sélection · clic droit sur un son : *Trouver des sons
similaires* · sur la waveform : molette = zoom, Maj+molette = défilement, clic = positionner,
glisser = sélectionner (puis *Boucler la sélection* ou *Trouver des sons similaires à la sélection*).

## Où sont mes données ?

| Dossier | Contenu |
|---|---|
| `data/libraries` | définition portable de chaque bibliothèque (dossiers, cache, modèles, taxonomie) |
| cache choisi (défaut `data/cache`) | base, waveforms, embeddings et index, **par modèle et par version** |
| `data/models` | poids des modèles installés |
| `data/logs`, `data/reports` | journaux et preuves de validation |
| `app/` | application (remplaçable par une mise à jour) · `runtime/` : Python privé, moteur IA, mises à jour |

Changer de modèle ou de version n'efface rien : les anciennes données restent jusqu'à ce que vous les
supprimiez (onglet *File d'analyse*). Une réanalyse ne supprime jamais vos tags ni vos catégories.

## Limites connues (version 0.1.1)

Validé uniquement sur cette machine Windows 10 x64 + RTX 3090. Linux et macOS : jamais exécutés.
L'installation utilise le Python du système pour créer les environnements privés : ce n'est pas un
installeur autonome « sans Python ». Les mises à jour de l'application viennent du dépôt
`MrMybal/CyTools_AudioLibrary` (onglet *Mises à jour*), mais aucune release n'y est encore publiée : le mécanisme
n'a été testé qu'avec des archives de test. Audio Flamingo 3 est déclaré dans le
registre mais n'a pas d'adaptateur. Détails, chiffres mesurés et preuves : `app/Docs/AudioLibrary-Validation.md`.

CLI, MCP et commandes développeur : `app/README.md`.

Maintenance : Cyberalien. Licence : GPL-3.0-only, texte complet dans `LICENSE`. Les moteurs et les poids des modèles
gardent leurs propres licences, listées dans l'onglet *Options*.
