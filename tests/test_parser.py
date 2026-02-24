"""Tests for parser, analysis, and export modules."""

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from capacidad.parser import load_csv, validate, _parse_num
from capacidad.analysis import (
    diagnose_node,
    filter_nodes,
    summary_by_region,
    top_nodes,
    binding_criteria_distribution,
    search_nodes,
    blocked_nodes,
)
from capacidad.export import to_sqlite, to_json, to_parquet


# ── Parser unit tests ────────────────────────────────────────────────────────

class TestParseNum:
    def test_integer(self):
        assert _parse_num("250") == 250.0

    def test_dot_thousands(self):
        assert _parse_num("1.310") == 1310.0

    def test_empty(self):
        assert _parse_num("") == 0.0

    def test_na(self):
        assert _parse_num("N/A") == 0.0

    def test_na_with_spaces(self):
        assert _parse_num(" N/A ") == 0.0

    def test_none(self):
        assert _parse_num(None) == 0.0

    def test_nan(self):
        assert _parse_num(float("nan")) == 0.0


# ── Validation tests (require downloaded CSV) ────────────────────────────────

class TestValidation:
    def test_row_count(self, df):
        assert len(df) == 937

    def test_column_count(self, df):
        # 61 original + 7 derived
        assert len(df.columns) >= 61

    def test_total_cep_ch(self, df):
        total = int(df["disp_dem_cep_ch"].sum())
        assert total == 39_643

    def test_total_no_cep(self, df):
        total = int(df["disp_dem_no_cep"].sum())
        assert total == 63_732

    def test_total_cep_sh_is_zero(self, df):
        assert int(df["disp_dem_cep_sh"].sum()) == 0

    def test_cataluna_count(self, df):
        assert len(df[df["ccaa"] == "Cataluña"]) == 118

    def test_unique_ccaa(self, df):
        assert df["ccaa"].nunique() == 18

    def test_concurso_nodes(self, df):
        assert df["is_concurso"].sum() == 76

    def test_validate_all_pass(self, df):
        checks = validate(df)
        for name, result in checks.items():
            assert result["ok"], f"Validation failed: {name}"


# ── Analysis tests ───────────────────────────────────────────────────────────

class TestAnalysis:
    def test_diagnose_escatron(self, df):
        diag = diagnose_node(df, "ESCATRON 400")
        assert diag["status"] == "BLOCKED_TECHNICAL"
        assert diag["available"]["CEP_CH"] == 0
        assert "Din1" in diag["binding_criteria"]["CEP_CH"]
        assert "Est_Dem" in diag["binding_criteria"]["CEP_CH"]

    def test_diagnose_abanillas(self, df):
        diag = diagnose_node(df, "ABANILLAS 400")
        assert diag["status"] == "AVAILABLE"
        assert diag["available"]["CEP_CH"] == 753

    def test_diagnose_not_found(self, df):
        diag = diagnose_node(df, "NONEXISTENT_NODE_12345")
        assert "error" in diag

    def test_summary_by_region(self, df):
        summary = summary_by_region(df)
        assert len(summary) == 18
        assert summary["total_mw"].sum() == 39_643

    def test_top_nodes(self, df):
        result = top_nodes(df, n=10)
        assert len(result) == 10
        # Should be sorted descending
        assert result["disp_dem_cep_ch"].is_monotonic_decreasing

    def test_filter_by_ccaa(self, df):
        result = filter_nodes(df, ccaa="Galicia")
        assert all(result["ccaa"] == "Galicia")
        assert len(result) == 60

    def test_filter_by_min_mw(self, df):
        result = filter_nodes(df, min_mw=500)
        assert all(result["disp_dem_cep_ch"] >= 500)

    def test_filter_only_available(self, df):
        result = filter_nodes(df, only_available=True)
        assert all(result["disp_dem_cep_ch"] > 0)

    def test_binding_criteria_distribution(self, df):
        dist = binding_criteria_distribution(df)
        assert len(dist) > 0
        # Din1_Zona should be the most common
        assert dist.iloc[0]["criterion"] == "Din1_Zona"

    def test_search_nodes(self, df):
        result = search_nodes(df, "ABANT")
        assert len(result) > 0
        assert any("ABANTO" in n for n in result["nudo"])

    def test_blocked_nodes(self, df):
        result = blocked_nodes(df)
        assert len(result) > 0
        assert all(result.index.duplicated() == False)

    def test_blocked_technical(self, df):
        result = blocked_nodes(df, reason="technical")
        assert all(result["is_blocked_technical"])

    def test_blocked_regulatory(self, df):
        result = blocked_nodes(df, reason="regulatory")
        assert all(result["is_blocked_regulatory"])


# ── Export tests ─────────────────────────────────────────────────────────────

class TestExport:
    def test_to_sqlite(self, df, tmp_path):
        path = to_sqlite(df, tmp_path / "test.db")
        assert path.exists()
        conn = sqlite3.connect(path)
        count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        assert count == 937
        conn.close()

    def test_to_json(self, df, tmp_path):
        path = to_json(df, tmp_path / "test.json")
        assert path.exists()
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data) == 937

    def test_to_parquet(self, df, tmp_path):
        path = to_parquet(df, tmp_path / "test.parquet")
        assert path.exists()
        reloaded = pd.read_parquet(path)
        assert len(reloaded) == 937

    def test_sqlite_roundtrip(self, df, tmp_path):
        """Export to SQLite, re-read, verify data integrity."""
        path = to_sqlite(df, tmp_path / "roundtrip.db")
        conn = sqlite3.connect(path)
        reloaded = pd.read_sql("SELECT * FROM nodes", conn)
        conn.close()
        assert len(reloaded) == 937
        assert int(reloaded["disp_dem_cep_ch"].sum()) == 39_643
