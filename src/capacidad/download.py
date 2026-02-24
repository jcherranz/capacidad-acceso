"""Download and extract REE demand access capacity ZIP file."""

import zipfile
from pathlib import Path

import requests

from capacidad.models import DATA_RAW, DEFAULT_ZIP_URL


def download_csv(
    url: str = DEFAULT_ZIP_URL,
    dest_dir: str | Path = DATA_RAW,
) -> Path:
    """Download ZIP from REE and extract CSV.

    Args:
        url: URL of the ZIP file.
        dest_dir: Directory to save extracted CSV.

    Returns:
        Path to the extracted CSV file.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    zip_name = url.rsplit("/", 1)[-1]
    zip_path = dest_dir / zip_name

    # Download
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    zip_path.write_bytes(resp.content)

    # Extract
    with zipfile.ZipFile(zip_path, "r") as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        if not csv_names:
            raise ValueError(f"No CSV found in {zip_path}")
        zf.extractall(dest_dir)
        csv_path = dest_dir / csv_names[0]

    return csv_path
