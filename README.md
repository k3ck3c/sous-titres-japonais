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

yt-dlp --cookies-from-browser firefox  --js-runtimes node --no-mtime --restrict-filenames --write-auto-subs -x --audio-format mp3 url-youtube

explications des options

--cookies-from-browser firefox  --js-runtimes node 

pour éviter certaines erreurs 403 lors du téléchargement

évidemment j'utilise Firefox mais adaptez avec votre navigateur

--no-mtime permet d'avoir le fichier .mp3 à la date actuelle et pas à la date de publication su Youtube

--restrict-filenames permet d'avoir un nom de fichier .mp3 avec seulement des caractères alphanumériques, pas d'émoticones ou autres caractères

--write-auto-subs écrit les sous-titres si il y en a

-x pour extract 

--audio-format pour créer un fichier .mp3

si on n'a pas de sous-titres, on va les créer avec whisper

 whisper --fp16 False  --language Japanese \
  --task transcribe \
  --model medium \
  --output_format srt fichier.mp3 > fichier.srt

 pour des sous-titres en japonais

 whisper --fp16 False --language fr fichier.mp3 > fichier.srt

 pour des sous-titres en français

 le fait d'indiquer le langage évite à whisper de le déterminer lui-même pendant les 30 premières secondes

 attention, la commande whisper prend autour de 30 minutes pour un fichier audio de 4 minutes sur mon PC avec un processeur core i5

 il est possible de payer quelques centimes pour faire cela en quelques secondes sur un service payant genre

 https://www.lemonfox.ai/

 ou plein d'autres
 

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

on peut le transformer avec le script conv_kanji_hiragana.sh , qui prend 

- le fichier de sous-titres en entrée

- donne un fichier résultat en sortie avec idéogramme et hiragana

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

On va créer une image fixe noire, et transformer le fichier audio (.mp3) en vidéo (.mp4) avec une image fixe noire, vu qu'on ne peut afficher des sous-titres dans un fichier audio

création de l'imga fixe noire

convert -size 1280x720 xc:black black.png

cela sera fait une seule fois, ce fichier black.png sera re-utilisé par la suite 

conversion du fichier .mp3 en .mp4

ffmpeg -loop 1 -framerate 2 -i black.png -i audio.mp3 -shortest -c:v libx264 -c:a copy video.mp4


le script Python deepl-jp-fr.py a besoin d'une clé Deepl

il suffit de s'inscrire et demander un compte gratuit, la limite est large pour un particulier

créer une clé d'API

faire 

export DEEPL_API_KEY="abc123def456ghi789"

(remplacer la chaine dans la ligne précédente par votre clé d'API)

avant de lancer le script

exemple pour la chanson kono machi, à partir d'un fichier de sous-titres japonais qui ressemble à

1
00:00:00,000 --> 00:00:29,980
作詞・作曲 初音ミク

2
00:00:30,000 --> 00:00:44,780
この街の空にも星は瞬く

3
00:00:44,780 --> 00:00:52,960
今はただ姿を隠してるだけ

on obtient en résultat

1
00:00:00,000 --> 00:00:29,980
Paroles et musique de Hatsune Miku

2
00:00:30,000 --> 00:00:44,780
Les étoiles scintillent également dans le ciel de cette ville.

3
00:00:44,780 --> 00:00:52,960
Aujourd'hui, ils se cachent à la vue de tous.



