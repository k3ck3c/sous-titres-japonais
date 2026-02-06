#!/bin/bash
infile="$1"
if [ -z black.png ];
then  convert -size 1280x720 xc:black black.png
fi
ffmpeg -loop 1 -framerate 2 -i ~/black.png -i "$1" -shortest -c:v libx264 -c:a copy "${infile%.*}".mp4

