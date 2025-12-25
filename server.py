from flask import Flask, request, jsonify, send_from_directory, render_template_string
from pathlib import Path
import subprocess
import shlex
import time
import os
import shutil

APP_DIR = Path(__file__).parent
OUTPUTS = APP_DIR / "outputs"
OUTPUTS.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=str(APP_DIR / "static"), static_url_path="/static")


def run(cmd, cwd=None):
    proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return proc.returncode, proc.stdout


def process_with_kakasi(in_srt: Path, out_srt: Path) -> bool:
    """
    Read `in_srt`, write to `out_srt`. For each non-empty, non-timestamp line,
    append kakasi -JH output on the next line (mirrors conv_kanji_hiragana.sh behavior).
    Returns True on success, False if kakasi not found or error.
    """
    kakasi_path = shutil.which('kakasi')
    if not kakasi_path:
        return False

    try:
        with in_srt.open('r', encoding='utf-8', errors='replace') as fin, out_srt.open('w', encoding='utf-8') as fout:
            for raw in fin:
                line = raw.rstrip('\n')
                # copy timestamp lines and short/empty lines as-is
                if (not line) or (len(line) < 3) or ('-->' in line):
                    fout.write(line + '\n')
                    continue

                fout.write(line + '\n')
                # run kakasi for this single line
                proc = subprocess.run([kakasi_path, '-JH', '-i', 'utf8', '-o', 'utf8'], input=line, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if proc.returncode == 0:
                    # kakasi may output trailing newlines
                    out_line = proc.stdout.rstrip('\n')
                    fout.write(out_line + '\n')
                else:
                    # on kakasi error, write an empty line (keep original behavior tolerant)
                    fout.write('\n')
        return True
    except Exception:
        return False


@app.route('/')
def index():
    return send_from_directory(str(APP_DIR / "static"), "index.html")


@app.route('/process', methods=['POST'])
def process():
    data = request.get_json()
    url = data.get('url')
    lang = data.get('lang', 'ja')
    if not url:
        return jsonify({'error': 'missing url'}), 400

    ts = time.strftime('%Y%m%d-%H%M%S')
    job_dir = OUTPUTS / f"job-{ts}"
    job_dir.mkdir(parents=True, exist_ok=True)

    logs = []

    # 1) yt-dlp: download audio and attempt automatic subtitles
    ytdlp_cmd = [
        'yt-dlp', '--no-mtime', '--restrict-filenames', '--write-auto-subs', '-x',
        '--audio-format', 'mp3', '-o', '%(title)s.%(ext)s', url
    ]
    rc, out = run(ytdlp_cmd, cwd=str(job_dir))
    logs.append({'cmd': ' '.join(ytdlp_cmd), 'rc': rc, 'out': out})
    if rc != 0:
        return jsonify({'error': 'yt-dlp failed', 'logs': logs}), 500

    # find the mp3 file
    files = list(job_dir.glob('*.mp3'))
    if not files:
        return jsonify({'error': 'no audio file found', 'logs': logs}), 500
    audio = files[0]

    # find any existing srt
    srts = list(job_dir.glob('*.srt'))
    srt_path = None
    if srts:
        srt_path = srts[0]
    else:
        # run whisper to create srt
        whisper_out = job_dir / (audio.stem + '.srt')
        whisper_cmd = ['whisper', '--fp16', 'False', '--language', lang, str(audio)]
        rc, out = run(whisper_cmd, cwd=str(job_dir))
        logs.append({'cmd': ' '.join(whisper_cmd), 'rc': rc, 'out': out})
        # try to locate produced srt
        produced = list(job_dir.glob('*.srt'))
        if produced:
            srt_path = produced[0]
        else:
            # fallback: write stdout to file
            try:
                whisper_out.write_text(out, encoding='utf-8')
                srt_path = whisper_out
            except Exception:
                return jsonify({'error': 'whisper failed to produce srt', 'logs': logs}), 500

    # convert with kakasi (Python implementation mirroring conv_kanji_hiragana.sh)
    converted = None
    out_srt = job_dir / (srt_path.stem + '.kana.srt')
    ok = process_with_kakasi(srt_path, out_srt)
    logs.append({'cmd': 'kakasi (python)', 'rc': 0 if ok else 1, 'out': f'kakasi produced: {out_srt.exists()}'} )
    if ok and out_srt.exists():
        converted = out_srt
    else:
        # fallback to existing shell script if present
        conv_script = APP_DIR / 'conv_kanji_hiragana.sh'
        if conv_script.exists() and os.access(conv_script, os.X_OK):
            conv_cmd = [str(conv_script), str(srt_path), str(out_srt)]
            rc, out = run(conv_cmd, cwd=str(APP_DIR))
            logs.append({'cmd': ' '.join(conv_cmd), 'rc': rc, 'out': out})
            if rc == 0 and out_srt.exists():
                converted = out_srt

    result = {
        'audio': f'/outputs/{job_dir.name}/{audio.name}',
        'srt': f'/outputs/{job_dir.name}/{srt_path.name}',
        'converted_srt': f'/outputs/{job_dir.name}/{converted.name}' if converted else None,
        'logs': logs,
    }
    return jsonify(result)


@app.route('/outputs/<job>/<path:filename>')
def outputs(job, filename):
    d = OUTPUTS / job
    return send_from_directory(str(d), filename)


@app.route('/jobs')
def jobs():
    result = []
    for p in sorted(OUTPUTS.iterdir() if OUTPUTS.exists() else []):
        if not p.is_dir():
            continue
        job = p.name
        audio = None
        srt = None
        converted = None
        for f in p.iterdir():
            if f.suffix.lower() == '.mp3' and audio is None:
                audio = f.name
            if f.suffix.lower() == '.srt':
                if f.name.endswith('.kana.srt'):
                    converted = f.name
                else:
                    # prefer the first .srt that's not the kana file
                    if srt is None:
                        srt = f.name
        result.append({'job': job, 'audio': f'/outputs/{job}/{audio}' if audio else None,
                       'srt': f'/outputs/{job}/{srt}' if srt else None,
                       'converted_srt': f'/outputs/{job}/{converted}' if converted else None})
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
