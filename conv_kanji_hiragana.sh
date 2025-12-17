#!/bin/bash
infile="$1"
outfile="$2"
# Si aucun 2ᵉ argument n'est donné, créer un nom de sortie par défaut
if [ -z "output" ]; then
  base="input
  output="{base}_kanji_hiragana.srt"
fi
while IFS= read -r line; do
    if [[ -z $line ]] || [ "${#line}" -lt 3 ] || [[ $line =~ "-->" ]]
    then
        echo "$line" >> "$outfile"
    else
        echo "$line" >> "$outfile"
	echo "$line" | kakasi -JH -i utf8 -o utf8 >> "$outfile"
    fi
done    < "$infile"

