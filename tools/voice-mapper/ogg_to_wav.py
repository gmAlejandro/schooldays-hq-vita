import argparse
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description="School Days HQ OGG -> WAV converter")
parser.add_argument("input_dir", help="Carpeta con OGG reconstruidos")
parser.add_argument("-o", "--output", required=True, help="Carpeta de salida")
args = parser.parse_args()

src = Path(args.input_dir)
dst = Path(args.output)
dst.mkdir(parents=True, exist_ok=True)

files = sorted(src.glob("*.ogg"))

print("=" * 70)
print(" School Days HQ OGG -> WAV")
print("=" * 70)
print(f"Entrada: {src}")
print(f"Salida:  {dst}")
print(f"OGG:     {len(files)}")
print()

ok = 0
fail = 0

for i, ogg in enumerate(files, 1):
    wav = dst / (ogg.stem + ".wav")

    cmd = [
        "ffmpeg",
        "-y",
        "-v", "error",
        "-i", str(ogg),
        "-vn",
        "-acodec", "pcm_s16le",
        str(wav)
    ]

    result = subprocess.run(cmd)

    if result.returncode == 0 and wav.exists() and wav.stat().st_size > 44:
        ok += 1
        print(f"[{i:3}/{len(files)}] OK   {ogg.name}")
    else:
        fail += 1
        print(f"[{i:3}/{len(files)}] FAIL {ogg.name}")

print()
print("=" * 70)
print("Resultado")
print("=" * 70)
print(f"OK:    {ok}")
print(f"FAIL:  {fail}")
print(f"Total: {len(files)}")
print(f"Salida: {dst}")