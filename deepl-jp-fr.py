import requests
import os
import sys
import subprocess

# --- Vérification MIME SRT ---
def check_srt(fichier):
    result = subprocess.run(
        ["file", "-i", fichier],
        capture_output=True,
        text=True
    )
    if "application/x-subrip" not in result.stdout:
        print("Fichier non reconnu comme SRT :", result.stdout.strip())
        sys.exit(1)

# --- DeepL config ---
DEEPL_KEY = os.getenv("DEEPL_API_KEY")
if not DEEPL_KEY:
    print("DEEPL_API_KEY non definie")
    sys.exit(1)

DEEPL_KEY = DEEPL_KEY.strip()
DEEPL_URL = "https://api-free.deepl.com/v2/translate"

def traduire(texte):
    r = requests.post(
        DEEPL_URL,
        headers={
            "Authorization": f"DeepL-Auth-Key {DEEPL_KEY}",
            "User-Agent": "deepl-python-script/1.0"
        },
        data={
            "text": texte,
            "source_lang": "JA",
            "target_lang": "FR"
        }
    )

    if r.status_code != 200:
        print("ERREUR DEEPL :", r.status_code, r.text)
        sys.exit(1)

    return r.json()["translations"][0]["text"]

# --- Traduction SRT standard (ultra robuste) ---
def traduire_srt(fichier_in):
    check_srt(fichier_in)

    with open(fichier_in, "r", encoding="utf-8") as f:
        lignes = f.readlines()

    out = []

    for ligne in lignes:
        l = ligne.strip()

        if not l:
            out.append("\n")
        elif l.isdigit():
            out.append(ligne)
        elif "-->" in l:
            out.append(ligne)
        else:
            # Toute autre ligne = texte à traduire
            out.append(traduire(l) + "\n")

    fichier_out = fichier_in.replace(".srt", ".fr.srt")
    with open(fichier_out, "w", encoding="utf-8") as f:
        f.writelines(out)

    print("Fichier cree :", fichier_out)

# --- Main ---
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage : python3 deep-jp-fr.py fichier.srt")
        sys.exit(1)

    traduire_srt(sys.argv[1])
