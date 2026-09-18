from pathlib import Path
import subprocess
import shutil
import sys


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe

    candidates = [
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python voice_audio.py <directorio_ogg> [salida]")
        sys.exit(1)

    source = Path(sys.argv[1])
    output = Path(sys.argv[2]) if len(sys.argv) >= 3 else source.parent / "wav"

    if not source.exists():
        print(f"No existe: {source}")
        sys.exit(1)

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("ERROR: No encuentro ffmpeg.")
        sys.exit(2)

    output.mkdir(parents=True, exist_ok=True)
    files = sorted(source.glob("*.ogg"))

    if not files:
        print("No hay archivos OGG.")
        sys.exit(1)

    print("=" * 70)
    print(" School Days HQ Voice Audio Converter")
    print("=" * 70)
    print(f"Entrada:  {source}")
    print(f"Salida:   {output}")
    print(f"FFmpeg:   {ffmpeg}")
    print(f"Archivos: {len(files)}")
    print()

    ok = 0
    failed = 0

    for i, src in enumerate(files, 1):
        dst = output / (src.stem + ".wav")

        cmd = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(src), "-vn", "-acodec", "pcm_s16le", str(dst)
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode == 0 and dst.exists() and dst.stat().st_size > 44:
            ok += 1
        else:
            failed += 1
            if dst.exists():
                try:
                    dst.unlink()
                except OSError:
                    pass
            print(f"[FAIL] {src.name}")
            if result.stderr:
                print(result.stderr.strip())

        if i % 25 == 0 or i == len(files):
            print(f"[{i}/{len(files)}] OK={ok} FAIL={failed}")

    print()
    print("=" * 70)
    print("Resultado")
    print("=" * 70)
    print(f"OK:   {ok}")
    print(f"FAIL: {failed}")
    print(f"Total: {len(files)}")
    print(f"Salida: {output}")


if __name__ == "__main__":
    main()
