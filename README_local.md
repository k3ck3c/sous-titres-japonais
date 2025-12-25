Local web interface for downloading audio and producing subtitles

Prerequisites (install system commands):
- yt-dlp
- ffmpeg (optional, for later video creation)
- whisper (OpenAI's whisper CLI) or compatible whisper CLI in PATH
- kakasi and/or the included `conv_kanji_hiragana.sh` script

Python requirements:
```
pip install -r requirements.txt
```

Run locally:
```
python server.py
```
Open http://127.0.0.1:5000 in your browser.

What it does:
- downloads audio (mp3) and automatic subs with `yt-dlp`
- if no subs exist, runs `whisper` to create an SRT
- if `conv_kanji_hiragana.sh` is executable, it will be called to produce a kana/converted SRT
- results are available under `/outputs/...` links

Notes:
- This is intentionally minimal. For robustness and production use add job queueing, streaming logs, authentication.
