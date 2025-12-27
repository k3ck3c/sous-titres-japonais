from flask import Flask, request, jsonify, send_from_directory, render_template_string, Response
from pathlib import Path
import subprocess
import shlex
import time
import os
import shutil
import threading
import json
import io

APP_DIR = Path(__file__).parent
OUTPUTS = APP_DIR / "outputs"
OUTPUTS.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=str(APP_DIR / "static"), static_url_path="/static")


def run(cmd, cwd=None):
    proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return proc.returncode, proc.stdout


def run_proc_stream(cmd, cwd, logfile_path):
    """Run command and append stdout/stderr to logfile_path in real time. Measure elapsed time."""
    import time as time_module
    with open(logfile_path, 'a', encoding='utf-8') as lf:
        lf.write(f"\n>>> RUN: {' '.join(cmd)}\n")
        lf.flush()
        start = time_module.time()
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            lf.write(line)
            lf.flush()
        proc.wait()
        elapsed = time_module.time() - start
        lf.write(f">>> RETURN CODE: {proc.returncode}\n")
        lf.write(f">>> ELAPSED: {elapsed:.2f}s\n")
        lf.flush()
        return proc.returncode


def write_log(job_dir, msg):
    p = job_dir / 'log.txt'
    with open(p, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')


def process_job(job_dir: Path, url: str, lang: str):
    logp = job_dir / 'log.txt'
    write_log(job_dir, f'Starting job for url={url} lang={lang}')

    # yt-dlp
    ytdlp_cmd = [
        'yt-dlp', '--no-mtime', '--restrict-filenames', '--write-auto-subs', '-x',
        '--audio-format', 'mp3', '-o', '%(title)s.%(ext)s', url
    ]
    rc = run_proc_stream(ytdlp_cmd, str(job_dir), str(logp))
    if rc != 0:
        write_log(job_dir, 'yt-dlp failed')
        (job_dir / 'result.json').write_text(json.dumps({'error': 'yt-dlp failed'}), encoding='utf-8')
        return

    # find mp3
    files = list(job_dir.glob('*.mp3'))
    if not files:
        write_log(job_dir, 'no audio file found')
        (job_dir / 'result.json').write_text(json.dumps({'error': 'no audio'}), encoding='utf-8')
        return
    audio = files[0]
    write_log(job_dir, f'Found audio: {audio.name}')

    # find srt
    srts = list(job_dir.glob('*.srt'))
    srt_path = None
    if srts:
        srt_path = srts[0]
        write_log(job_dir, f'Found existing srt: {srt_path.name}')
    else:
        whisper_out = job_dir / (audio.stem + '.srt')
        whisper_cmd = ['whisper', '--fp16', 'False', '--language', lang, str(audio)]
        rc = run_proc_stream(whisper_cmd, str(job_dir), str(logp))
        if rc != 0:
            write_log(job_dir, 'whisper failed')
        produced = list(job_dir.glob('*.srt'))
        if produced:
            srt_path = produced[0]
            write_log(job_dir, f'Whisper produced srt: {srt_path.name}')
        else:
            # fallback: capture last part of log and write to srt
            text = logp.read_text(encoding='utf-8')
            whisper_out.write_text(text, encoding='utf-8')
            srt_path = whisper_out
            write_log(job_dir, f'Wrote fallback srt: {srt_path.name}')

    # kakasi processing
    out_srt = job_dir / (srt_path.stem + '.kana.srt')
    ok = process_with_kakasi(srt_path, out_srt, logp)
    write_log(job_dir, f'kakasi ok={ok} output={out_srt.name}')

    # try to produce a French translation of the srt
    fr_srt = job_dir / (srt_path.stem + '.fr.srt')
    tr_ok = translate_srt(srt_path, fr_srt, src='ja', tgt='fr', logfile_path=logp)
    write_log(job_dir, f'translation ok={tr_ok} output={fr_srt.name if tr_ok else None}')

    result = {
        'audio': f'/outputs/{job_dir.name}/{audio.name}',
        'srt': f'/outputs/{job_dir.name}/{srt_path.name}',
        'converted_srt': f'/outputs/{job_dir.name}/{out_srt.name}' if out_srt.exists() else None,
        'translated_srt': f'/outputs/{job_dir.name}/{fr_srt.name}' if fr_srt.exists() else None,
    }
    (job_dir / 'result.json').write_text(json.dumps(result), encoding='utf-8')
    write_log(job_dir, 'JOB DONE')


def process_with_kakasi(in_srt: Path, out_srt: Path, logfile_path: Path = None) -> bool:
    """
    Read `in_srt`, write to `out_srt`. For each non-empty, non-timestamp line,
    append kakasi -JH output on the next line (mirrors conv_kanji_hiragana.sh behavior).
    Returns True on success, False if kakasi not found or error.
    """
    import time as time_module
    kakasi_path = shutil.which('kakasi')
    if not kakasi_path:
        return False

    try:
        start = time_module.time()
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
        elapsed = time_module.time() - start
        if logfile_path:
            with open(logfile_path, 'a', encoding='utf-8') as lf:
                lf.write(f">>> kakasi ELAPSED: {elapsed:.2f}s\n")
        return True
    except Exception:
        return False


def translate_srt(in_srt: Path, out_srt: Path, src='ja', tgt='fr', logfile_path: Path = None) -> bool:
    """
    Translate subtitle text lines from `src` to `tgt` language, writing a new srt with same timing.
    Tries to use `trans` (translate-shell) or `argos-translate-cli` if available.
    Returns True on success, False if no translator found or error.
    """
    import time as time_module
    trans_path = shutil.which('trans')
    argos_path = shutil.which('argos-translate-cli') or shutil.which('argos')
    if not trans_path and not argos_path:
        return False

    try:
        start = time_module.time()
        with in_srt.open('r', encoding='utf-8', errors='replace') as fin, out_srt.open('w', encoding='utf-8') as fout:
            block = []
            for line in fin:
                stripped = line.rstrip('\n')
                if stripped == '':
                    # process block
                    if block:
                        for l in _translate_block(block, trans_path, argos_path, src, tgt, out_srt):
                            fout.write(l + '\n')
                        block = []
                    fout.write('\n')
                else:
                    block.append(stripped)
            if block:
                for l in _translate_block(block, trans_path, argos_path, src, tgt, out_srt):
                    fout.write(l + '\n')
        elapsed = time_module.time() - start
        if logfile_path:
            with open(logfile_path, 'a', encoding='utf-8') as lf:
                lf.write(f">>> translation ELAPSED: {elapsed:.2f}s\n")
        return True
    except Exception:
        return False


def _translate_block(block_lines, trans_path, argos_path, src, tgt, out_srt):
    # block_lines is list of lines for a subtitle block
    # keep index and timing lines, translate text lines
    out = []
    idx = 0
    if block_lines and block_lines[0].isdigit():
        out.append(block_lines[0])
        idx = 1
    if idx < len(block_lines):
        out.append(block_lines[idx])
        idx += 1
    # remaining lines are text
    text = '\n'.join(block_lines[idx:]) if idx < len(block_lines) else ''
    if not text:
        return out

    # choose translator
    translated = None
    if trans_path:
        # trans -b :fr "text"
        try:
            proc = subprocess.run([trans_path, '-b', f':{tgt}', text], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if proc.returncode == 0:
                translated = proc.stdout.strip()
        except Exception:
            translated = None
    if translated is None and argos_path:
        try:
            # argos-translate-cli -s ja -t fr
            proc = subprocess.run([argos_path, '-s', src, '-t', tgt], input=text, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if proc.returncode == 0:
                translated = proc.stdout.strip()
        except Exception:
            translated = None

    if translated is None:
        # fallback: keep original text
        translated = text

    # write translated as single or multiple lines
    for tline in translated.split('\n'):
        out.append(tline)
    return out


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

    # start background thread
    t = threading.Thread(target=process_job, args=(job_dir, url, lang), daemon=True)
    t.start()

    return jsonify({'job': job_dir.name})


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
                elif f.name.endswith('.fr.srt'):
                    translated = f.name
                else:
                    # prefer the first .srt that's not the kana file
                    if srt is None:
                        srt = f.name
        result.append({'job': job, 'audio': f'/outputs/{job}/{audio}' if audio else None,
                       'srt': f'/outputs/{job}/{srt}' if srt else None,
                       'converted_srt': f'/outputs/{job}/{converted}' if converted else None,
                       'translated_srt': f'/outputs/{job}/{translated}' if ("translated" in locals() and translated) else None})
    return jsonify(result)


@app.route('/events/<job>')
def events(job):
    job_dir = OUTPUTS / job
    if not job_dir.exists():
        return jsonify({'error': 'no such job'}), 404

    def gen():
        logp = job_dir / 'log.txt'
        # ensure log file exists
        if not logp.exists():
            open(logp, 'a').close()
        with open(logp, 'r', encoding='utf-8') as f:
            # send existing lines
            for line in f:
                yield f'data: {line.strip()}\n\n'
            # now wait for new lines and final result
            resultp = job_dir / 'result.json'
            while True:
                where = f.tell()
                line = f.readline()
                if line:
                    yield f'data: {line.strip()}\n\n'
                else:
                    if resultp.exists():
                        try:
                            res = json.loads(resultp.read_text(encoding='utf-8'))
                        except Exception:
                            res = {'error': 'invalid result.json'}
                        yield 'event: result\n'
                        yield f'data: {json.dumps(res)}\n\n'
                        break
                    time.sleep(0.5)
                    f.seek(where)

    return Response(gen(), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
