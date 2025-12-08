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

- yt-dlp   disponible à https://github.com/yt-dlp/yt-dlp/wiki/Installation
  
- whisper disponible à https://github.com/openai/whisper

- kakasi disponible à http://kakasi.namazu.org/index.html.en


exemple pour extraire l'audio d'une vidéo de chanson

yt-dlp --no-mtime --restrict-filenames --write-auto-subs -x --audio-format mp3

--no-mtime permet d'avoir le fichier .mp3 à la date actuelle

--restrict-filenames permet d'avoir un nom de fichier .mp3 avec seulement des caractères alphanumériques, pas d'émoticones ou autres caractères

--write-auto-subs écrit les sous-titres si il y en a

-x pour extract 

--audio-format pour créer un fichier .mp3

si on n'a pas de sous-titres, on va les créer avec whisper

 whisper --fp16 False fichier.mp3 > fichier.srt

 une fois qu'on a un fichier de sous-titres en japonais, on vérifie si la syntaxe du fichier de sous-titres est correcte

 exemple de fichier de sous-titres correct (en anglais)

 
1

00:00:08,640 --> 00:00:14,080

It's like a dream.


2

00:00:14,720 --> 00:00:20,320

For example it's like a lie.


3

00:00:20,500 --> 00:00:24,880

The cruel morning,


donc une ligne avec un nombre qui s'incrémente 

un horodatage avec heures minutes secondes séparés par des : et des millièmes de seconde séparés par une virgule

un texte de une ou plusieurs lignes

quand un fichier de sous-titres ne respecte pas cette syntaxe, mpv affiche un message du type

Can not open external file xxx.srt

cela signifie que le fichier est bien trouvé par mpv, mais que ce n'est pas un fichier de sous-titres correct

si on prend un fichier de sous-titres japonais, par exemple

1

00:00.000 --> 00:08.000

作詞・作曲・編曲 初音ミク


2

00:08.000 --> 00:20.000

それは夢のように まるで嘘のように


3

00:20.000 --> 00:34.000

残酷な朝は 全てをうまいさほった

on peut le transformer avec le script conv_kanji_hiragana.sh , qui prend le fichier de sous-titres en entrée et le fichier résultat avec idéogramme et hiragana

le fichier de sous-titres précédent devient

1

00:00.000 --> 00:08.000

作詞・作曲・編曲 初音ミク

さくし・さっきょく・へんきょく はつおとミク


2

00:08.000 --> 00:20.000

それは夢のように まるで嘘のように

それはゆめのように まるでうそのように

3

00:20.000 --> 00:34.000

残酷な朝は 全てをうまいさほった

ざんこくなあさは すべてをうまいさほった



Pour savoir si un fichier de sous-titres sera lu par mpv, il faut faire

file -i fichier.srt

si on a dans le résultat

: application/x-subrip

alors c'est un fichier de sous-titres, il sera pris en compte par mpv 
