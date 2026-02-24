"""Core CSV parser for REE demand access capacity data."""

from pathlib import Path

import pandas as pd

from capacidad.models import (
    COLUMN_NAMES,
    DEFAULT_CSV,
    EXPECTED_COLS,
    EXPECTED_ROWS,
    NUMERIC_COLUMNS,
    POSITION_COLUMNS,
    STRING_COLUMNS,
)


def _parse_num(val) -> float:
    """Convert REE CSV numeric value to float.

    Handles dot-as-thousands separator, N/A, empty strings, whitespace.
    """
    if pd.isna(val):
        return 0.0
    val = str(val).strip()
    if val in ("", "N/A"):
        return 0.0
    # Remove dots (thousands separator, NOT decimal)
    val = val.replace(".", "")
    try:
        return float(val)
    except ValueError:
        return 0.0


def _parse_checkmark(val) -> bool:
    """Convert checkmark (✓) or empty to boolean."""
    if pd.isna(val):
        return False
    return str(val).strip() == "✓"


def load_csv(filepath: str | Path | None = None) -> pd.DataFrame:
    """Load and parse the REE demand access capacity CSV file.

    Args:
        filepath: Path to CSV file. Defaults to data/raw/2026_02_20_GRT_demanda.csv

    Returns:
        DataFrame with 937 rows × 61 columns, cleaned and typed.
    """
    if filepath is None:
        filepath = DEFAULT_CSV
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(
            f"CSV not found: {filepath}\n"
            "Run 'capacidad download' to fetch it."
        )

    # Read data rows: skip 4 merged header rows, handle BOM
    df = pd.read_csv(
        filepath,
        sep=";",
        header=None,
        skiprows=4,
        encoding="utf-8-sig",
        dtype=str,
    )

    # Assign column names
    df.columns = COLUMN_NAMES[: len(df.columns)]

    # Convert numeric columns (dot = thousands separator)
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(_parse_num)

    # Convert position columns (checkmarks → booleans)
    for col in POSITION_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(_parse_checkmark)

    # Strip whitespace from string columns
    for col in STRING_COLUMNS:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()

    # Derived columns
    df["has_demand_bay"] = df["pos_con_E"] | df["pos_con_P"]
    df["is_blocked_technical"] = (
        (df["limitante_dem_cep_ch"] != "") & (df["disp_dem_cep_ch"] == 0)
    )
    df["is_blocked_regulatory"] = df["motivo_no_otorgable"] != ""
    df["has_wscr_alert"] = df["wscr_alertas"] != ""
    df["is_concurso"] = df["concurso"] == "SI"
    df["acuerdo_resuelto"] = df["estado_acuerdo"] == "SI"

    # Extract voltage from node name
    df["voltage_kv"] = df["nudo"].str.extract(r"(\d+)\s*$").astype(float)

    return df


def validate(df: pd.DataFrame) -> dict:
    """Validate parsed DataFrame against known aggregates.

    Returns dict with check results.
    """
    checks = {}
    checks["row_count"] = {
        "expected": EXPECTED_ROWS,
        "actual": len(df),
        "ok": len(df) == EXPECTED_ROWS,
    }
    checks["col_count"] = {
        "expected": EXPECTED_COLS,
        "actual": len(COLUMN_NAMES),
        "ok": len(df.columns) >= EXPECTED_COLS,
    }

    total_cep_ch = int(df["disp_dem_cep_ch"].sum())
    checks["total_cep_ch_mw"] = {
        "expected": 39_643,
        "actual": total_cep_ch,
        "ok": abs(total_cep_ch - 39_643) < 100,  # Allow small rounding
    }

    cataluna_count = len(df[df["ccaa"] == "Cataluña"])
    checks["cataluna_nodes"] = {
        "expected": 118,
        "actual": cataluna_count,
        "ok": cataluna_count == 118,
    }

    unique_ccaa = df["ccaa"].nunique()
    checks["unique_ccaa"] = {
        "expected": 18,
        "actual": unique_ccaa,
        "ok": unique_ccaa == 18,
    }

    return checks
