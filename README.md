# Capacidad de Acceso

Parser and analyzer for REE's demand access capacity data — Spain's 937-node, 400/220 kV transmission grid.

Data source: [REE Capacidad de Acceso](https://www.ree.es/es/clientes/generador/acceso-conexion) (February 2026 publication).

## What it does

- **Parses** the official REE CSV (BOM-encoded, semicolons, 4 header rows, dot-as-thousands)
- **Analyzes** available capacity by region, voltage, criterion, and node status
- **Generates narrative reports** — plain-English diagnostics for any substation
- **Exports** to SQLite, JSON, and Parquet
- **Visualizes** via Streamlit dashboard with filtering, charts, and node explorer

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick start

```bash
# Download latest CSV from REE
capacidad download

# Dataset overview
capacidad info

# Capacity by region
capacidad regions

# Top 20 nodes for data center siting
capacidad top

# Full diagnostic for a node
capacidad node "ABANILLAS 400"

# Prose report only (clean output for sharing)
capacidad report "ABANILLAS 400"

# Search nodes by name
capacidad search "ESCATRON"

# Blocked nodes
capacidad blocked --reason technical

# Export to all formats
capacidad export

# Launch web dashboard
capacidad dashboard
```

## Example report

```
ABANILLAS 400 — Región de Murcia (400 kV)

This node has 753 MW available for new power-electronics demand (CEP CH)
and 847 MW for conventional demand.

The binding constraint for power-electronics demand is WSCR (short-circuit
ratio) at this node. Conventional demand is limited to 847 MW by transient
stability (dynamic criterion 1) in the zone. Storage capacity is 847 MW,
limited by transient stability (dynamic criterion 1) in the zone.

No demand has been granted or is pending at this node.
The reference value agreement is not applicable (no distribution interface).
This node is not subject to competitive tender.

No WSCR security alerts. No substation configuration limitations.
```

## Project structure

```
src/capacidad/
  models.py      # 61 column definitions, paths, constants
  parser.py      # CSV loader (encoding, delimiters, type coercion)
  analysis.py    # Filter, aggregate, diagnose, generate_report
  export.py      # SQLite (with indexes), JSON, Parquet
  cli.py         # Typer CLI with 10 commands
  dashboard.py   # Streamlit app with 4 tabs
data/
  raw/           # Downloaded CSV/ZIP from REE
  processed/     # SQLite, JSON, Parquet exports
tests/           # 33 tests
```

## Key concepts

| Term | Meaning |
|------|---------|
| **CEP CH** | Power-electronics demand with harmonic compliance — the key metric for data centers, electrolysers |
| **CEP SH** | Power-electronics demand without harmonic compliance (always 0 MW in current data) |
| **NO CEP** | Conventional demand (motors, resistive loads) |
| **WSCR** | Weighted short-circuit ratio — limits power-electronics penetration |
| **Est_Dem / Est_Alm** | Steady-state thermal limits for demand / storage |
| **Din1 / Din2** | Transient stability criteria |
| **Concurso** | Competitive tender node (limited capacity, auction required) |

## Tests

```bash
pytest
```

## License

Private project.
