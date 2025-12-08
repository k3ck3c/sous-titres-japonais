#!/bin/bash
infile="$1"
outfile="$2"
while IFS= read -r line; do
    if [[ -z $line ]] || [ "${#line}" -lt 3 ] || [[ $line =~ "-->" ]]
    then
        echo "$line" >> "$outfile"
    else
        echo "$line" >> "$outfile"
	echo "$line" | kakasi -JH -i utf8 -o utf8 >> "$outfile"
    fi
done    < "$infile"

