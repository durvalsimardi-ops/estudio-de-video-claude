#!/usr/bin/env python3
"""Transcreve um vídeo ou áudio palavra a palavra.

Uso:
  .venv/bin/python ferramentas/transcrever.py <video-ou-audio> <saida.json> [--idioma pt] [--nomes "Café Aurora, Ana"]

Saída: lista de palavras [{"w": "palavra", "s": início, "e": fim}], em segundos.
No Mac com chip Apple usa o mlx-whisper (rápido). Nos outros computadores, o faster-whisper.
--nomes ajuda o Whisper a escrever certo nomes próprios e marcas.
"""
import json, os, subprocess, sys, tempfile

args = sys.argv[1:]
def opt(nome, padrao=None):
    if nome in args:
        i = args.index(nome); v = args[i + 1]; del args[i:i + 2]; return v
    return padrao
IDIOMA = opt("--idioma", "pt")
NOMES = opt("--nomes", "")
if len(args) < 2:
    print(__doc__); sys.exit(1)
ENTRADA, SAIDA = args[0], args[1]

with tempfile.TemporaryDirectory() as tmp:
    wav = os.path.join(tmp, "voz.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ENTRADA, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    prompt = f"Nomes: {NOMES}." if NOMES else None
    palavras = []
    try:
        import mlx_whisper
        r = mlx_whisper.transcribe(wav, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language=IDIOMA,
                                   word_timestamps=True, initial_prompt=prompt)
        for s in r["segments"]:
            for w in s.get("words", []):
                if w["word"].strip():
                    palavras.append({"w": w["word"].strip(), "s": round(w["start"], 3), "e": round(w["end"], 3)})
    except ImportError:
        from faster_whisper import WhisperModel
        modelo = WhisperModel("large-v3-turbo", device="auto", compute_type="auto")
        segs, _ = modelo.transcribe(wav, language=IDIOMA, word_timestamps=True, initial_prompt=prompt, vad_filter=False)
        for s in segs:
            for w in s.words or []:
                if w.word.strip():
                    palavras.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)})

os.makedirs(os.path.dirname(os.path.abspath(SAIDA)), exist_ok=True)
json.dump(palavras, open(SAIDA, "w"), ensure_ascii=False, indent=0)
print(f"ok · {len(palavras)} palavras · {SAIDA}")
