"""Export parsed data to SQLite, JSON, and Parquet formats."""

import json
import sqlite3
from pathlib import Path

import pandas as pd

from capacidad.models import DATA_PROCESSED


def to_sqlite(
    df: pd.DataFrame,
    filepath: str | Path | None = None,
    table_name: str = "nodes",
) -> Path:
    """Export DataFrame to SQLite with indexes.

    Args:
        df: Parsed capacity DataFrame.
        filepath: Output path. Defaults to data/processed/capacidad.db
        table_name: SQL table name.

    Returns:
        Path to the SQLite file.
    """
    if filepath is None:
        filepath = DATA_PROCESSED / "capacidad.db"
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(filepath)
    df.to_sql(table_name, conn, if_exists="replace", index=False)

    # Create indexes for common queries
    cursor = conn.cursor()
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_ccaa ON {table_name}(ccaa)")
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_nudo ON {table_name}(nudo)")
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_disp_cep_ch "
        f"ON {table_name}(disp_dem_cep_ch)"
    )
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_voltage ON {table_name}(voltage_kv)"
    )
    conn.commit()
    conn.close()
    return filepath


def to_json(
    df: pd.DataFrame,
    filepath: str | Path | None = None,
) -> Path:
    """Export DataFrame to JSON (records orientation).

    Args:
        df: Parsed capacity DataFrame.
        filepath: Output path. Defaults to data/processed/capacidad.json

    Returns:
        Path to the JSON file.
    """
    if filepath is None:
        filepath = DATA_PROCESSED / "capacidad.json"
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    records = json.loads(df.to_json(orient="records", force_ascii=False))
    filepath.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return filepath


def to_parquet(
    df: pd.DataFrame,
    filepath: str | Path | None = None,
) -> Path:
    """Export DataFrame to Parquet format.

    Args:
        df: Parsed capacity DataFrame.
        filepath: Output path. Defaults to data/processed/capacidad.parquet

    Returns:
        Path to the Parquet file.
    """
    if filepath is None:
        filepath = DATA_PROCESSED / "capacidad.parquet"
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    df.to_parquet(filepath, engine="pyarrow", index=False)
    return filepath
