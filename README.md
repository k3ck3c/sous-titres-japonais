# sous-titres-japonais
afficher des sous-titres de chansons japonaises en kanji, hiragana et français ou anglais

l'idée est de télécharger une vidéo de chanson sur YouTube

extraire l'audio

si il n'y a pas de sous-titres, les créer avec whisper

puis convertir l'audio (fichier .mp3) en vidéo avec une image fixe noire

afficher en haut le sous-titres avec 2 lignes

une avec les kanjis

une en hiragana, lisible sans avoir besoin de connaitre les 1945 kanjis de base

il faut installer 

- yt-dlp
  
- whisper

- kakasi


exemple pour extraire l'audio d'une vidéo de chanson

yt-dlp --no-mtime --restrict-filenames --write-auto-subs -x --audio-format mp3

--no-mtime permet d'avoir le fichier .mp3 à la date actuelle

--restrict-filenames permet d'avoir un nom de fichier .mp3 avec seulement des caractères alphanumériques, pas d'émoticones ou autres caractères

--write-auto-subs écrit les sous-titres si il y en a

-x pour extract 

--audio-format pour créer un fichier .mp3
