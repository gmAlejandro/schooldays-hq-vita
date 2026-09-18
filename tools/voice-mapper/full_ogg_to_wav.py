from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 3:
    print("Uso: python full_ogg_to_wav.py <input_ogg> <output_wav>")
    sys.exit(1)

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=True)

files = sorted(src.glob("*.ogg"))

print("=" * 70)
print(" School Days HQ OGG -> WAV")
print("=" * 70)
print(f"Entrada : {src}")
print(f"Salida  : {dst}")
print(f"Archivos: {len(files)}")
print()

ok = 0
fail = 0

for n, ogg in enumerate(files, 1):
    wav = dst / f"{ogg.stem}.wav"

    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", str(ogg),
            "-c:a", "pcm_s16le",
            str(wav)
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode == 0 and wav.exists() and wav.stat().st_size > 44:
        ok += 1
    else:
        fail += 1
        print(f"[FAIL] {ogg.name}")
        print(result.stderr.strip())

    if n % 50 == 0 or n == len(files):
        print(f"[{n:3}/{len(files)}] OK={ok} FAIL={fail}")

print()
print("=" * 70)
print("Resultado")
print("=" * 70)
print(f"OK   : {ok}")
print(f"FAIL : {fail}")
print(f"TOTAL: {len(files)}")
print()
print(f"Salida: {dst}")