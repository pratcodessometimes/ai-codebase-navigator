from pathlib import Path
import zipfile
import shutil


IGNORED_DIRECTORIES = {
    "node_modules",
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "dist",
    "build",
}


def extract_repository(zip_path: Path, extract_path: Path):
    if extract_path.exists():
        shutil.rmtree(extract_path)

    extract_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)


def get_repository_files(repository_path: Path):
    files = []

    for path in repository_path.rglob("*"):
        if not path.is_file():
            continue

        relative_path = path.relative_to(repository_path)

        if any(
            part in IGNORED_DIRECTORIES
            for part in relative_path.parts
        ):
            continue

        files.append(relative_path.as_posix())

    return files