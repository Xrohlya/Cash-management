"""Quarantine AppleDouble sidecars which pip mistakes for distributions."""
from pathlib import Path
import sys
import tempfile

APPLEDOUBLE = b"\x00\x05\x16\x07"


def clean_metadata(prefix, search_paths):
    prefix = Path(prefix).resolve()
    destination = None
    moved = 0
    for entry in search_paths:
        path = Path(entry).resolve()
        if path.name != "site-packages" or not path.is_relative_to(prefix):
            continue
        for sidecar in path.glob("._*.dist-info"):
            if sidecar.is_symlink() or not sidecar.is_file():
                continue
            with sidecar.open("rb") as stream:
                if stream.read(4) != APPLEDOUBLE:
                    continue
            if destination is None:
                backup = prefix / ".metadata-backup"
                backup.mkdir(exist_ok=True)
                destination = Path(tempfile.mkdtemp(prefix="appledouble-", dir=backup))
            sidecar.rename(destination / sidecar.name)
            moved += 1
    return moved


if __name__ == "__main__":
    count = clean_metadata(sys.prefix, sys.path)
    if count:
        print(f"Служебные файлы macOS перенесены из списка пакетов: {count}.")
