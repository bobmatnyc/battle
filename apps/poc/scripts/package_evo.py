"""Build the offline-capable Evo runtime bundle; never connect to a host."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ASSETS = {".html", ".js", ".css", ".jpg", ".txt", ".json"}


def main():
    destination = ROOT / "artifacts/evo/battle-poc.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as stage:
        archive = Path(stage) / destination.name
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
            for tree, extensions in (("battle", {".py"}), ("static", PUBLIC_ASSETS)):
                for path in sorted((ROOT / tree).rglob("*")):
                    relative = path.relative_to(ROOT)
                    if (path.suffix in extensions and path.is_file()
                            and path.resolve() == path and not any(
                                part.startswith(".") or part == "__pycache__" for part in relative.parts)):
                        bundle.write(path, relative)
            for required in ("battle/__main__.py", "static/index.html", "static/vendor/maplibre/LICENSE.txt"):
                bundle.getinfo(required)
        # Publish only the complete archive, leaving an earlier bundle intact on failure.
        archive.replace(destination)
    print(destination)


if __name__ == "__main__":
    main()
