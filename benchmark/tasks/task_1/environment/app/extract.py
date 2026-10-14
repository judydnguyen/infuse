import zipfile
from pathlib import Path

def extract_zip(zip_path: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            target_path = output_dir / member
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(target_path, "wb") as dst:
                dst.write(src.read())

if __name__ == "__main__":
    app_dir = Path(__file__).parent
    zip_path = app_dir / "input.zip"
    output_dir = app_dir / "output_dir"
    
    extract_zip(zip_path, output_dir)