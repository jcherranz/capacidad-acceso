"""Typer CLI for REE demand access capacity data."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from capacidad.models import CAPACITY_LABELS, DATA_PROCESSED, DEFAULT_CSV

app = typer.Typer(
    name="capacidad",
    help="REE demand access capacity parser and analyzer for Spain's transmission grid.",
)
console = Console()


def _load():
    """Load CSV with lazy import."""
    from capacidad.parser import load_csv
    return load_csv()


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------
@app.command()
def download(
    url: Optional[str] = typer.Option(None, help="ZIP URL override"),
):
    """Download REE demand access capacity CSV from REE."""
    from capacidad.download import download_csv
    from capacidad.models import DEFAULT_ZIP_URL

    target_url = url or DEFAULT_ZIP_URL
    console.print(f"Downloading from [blue]{target_url}[/blue] ...")
    path = download_csv(url=target_url)
    console.print(f"[green]Saved:[/green] {path}")


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------
@app.command()
def info(csv: Optional[Path] = typer.Option(None, help="Path to CSV")):
    """Show dataset summary and validation checks."""
    from capacidad.parser import load_csv, validate

    df = load_csv(csv)
    checks = validate(df)

    console.print(f"\n[bold]REE Demand Access Capacity — Dataset Summary[/bold]\n")
    console.print(f"  Rows:  {len(df)}")
    console.print(f"  Cols:  {len(df.columns)} ({61} original + {len(df.columns)-61} derived)")
    console.print(f"  CCAA:  {df['ccaa'].nunique()}")

    console.print(f"\n[bold]Key Aggregates[/bold]")
    console.print(f"  Total CEP CH demand:   {int(df['disp_dem_cep_ch'].sum()):>8,} MW")
    console.print(f"  Total CEP SH demand:   {int(df['disp_dem_cep_sh'].sum()):>8,} MW")
    console.print(f"  Total NO CEP demand:   {int(df['disp_dem_no_cep'].sum()):>8,} MW")
    console.print(f"  Total CEP storage:     {int(df['disp_alm_cep'].sum()):>8,} MW")
    console.print(f"  Total NO CEP storage:  {int(df['disp_alm_no_cep'].sum()):>8,} MW")

    nodes_avail = (df["disp_dem_cep_ch"] > 0).sum()
    console.print(f"\n  Nodes with CEP CH > 0: {nodes_avail} / {len(df)} ({100*nodes_avail/len(df):.0f}%)")
    console.print(f"  Nodes blocked:         {len(df) - nodes_avail}")
    console.print(f"  Concurso nodes:        {df['is_concurso'].sum()}")
    console.print(f"  Unresolved agreements: {(df['estado_acuerdo'] == 'NO').sum()}")
    console.print(f"  WSCR alerts:           {df['has_wscr_alert'].sum()}")

    console.print(f"\n[bold]Validation[/bold]")
    for name, result in checks.items():
        icon = "✓" if result["ok"] else "✗"
        color = "green" if result["ok"] else "red"
        console.print(f"  [{color}]{icon}[/{color}] {name}: {result['actual']} (expected {result['expected']})")
    console.print()


# ---------------------------------------------------------------------------
# regions
# ---------------------------------------------------------------------------
@app.command()
def regions(
    capacity_type: str = typer.Option("disp_dem_cep_ch", "--type", "-t",
                                       help="Capacity column to aggregate"),
):
    """Show capacity summary by Autonomous Community."""
    from capacidad.analysis import summary_by_region

    df = _load()
    summary = summary_by_region(df, capacity_col=capacity_type)

    table = Table(title="Capacity by Region")
    table.add_column("CCAA", style="cyan")
    table.add_column("Nodes", justify="right")
    table.add_column("Total MW", justify="right", style="green")
    table.add_column("Avg MW", justify="right")
    table.add_column("With Cap.", justify="right", style="green")
    table.add_column("Blocked", justify="right", style="red")
    table.add_column("Unresolved", justify="right", style="yellow")

    for _, row in summary.iterrows():
        table.add_row(
            row["ccaa"],
            str(row["nodes"]),
            f"{row['total_mw']:,}",
            str(row["avg_mw"]),
            str(row["nodes_with_capacity"]),
            str(row["nodes_blocked"]),
            str(row["unresolved_agreement"]),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# top
# ---------------------------------------------------------------------------
@app.command()
def top(
    n: int = typer.Option(20, "--n", "-n", help="Number of nodes"),
    capacity_type: str = typer.Option("disp_dem_cep_ch", "--type", "-t",
                                       help="Capacity column to rank"),
):
    """Show top N nodes by available capacity."""
    from capacidad.analysis import top_nodes

    df = _load()
    result = top_nodes(df, n=n, capacity_col=capacity_type)

    label = CAPACITY_LABELS.get(capacity_type, capacity_type)
    table = Table(title=f"Top {n} Nodes — {label}")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Node", style="cyan")
    table.add_column("CCAA")
    table.add_column("MW", justify="right", style="green")
    table.add_column("kV", justify="right")
    table.add_column("Binding Criterion")
    table.add_column("Concurso", justify="center")

    for i, (_, row) in enumerate(result.iterrows(), 1):
        table.add_row(
            str(i),
            row["nudo"],
            row["ccaa"],
            f"{int(row[capacity_type]):,}",
            str(int(row["voltage_kv"])) if row["voltage_kv"] else "",
            row["limitante_dem_cep_ch"],
            "SI" if row["is_concurso"] else "",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# node
# ---------------------------------------------------------------------------
@app.command()
def node(name: str = typer.Argument(..., help="Node name (e.g. 'ESCATRON 400')")):
    """Full diagnostic for a specific node."""
    from capacidad.analysis import diagnose_node

    df = _load()
    diag = diagnose_node(df, name)

    if "error" in diag:
        console.print(f"[red]{diag['error']}[/red]")
        if "matches" in diag:
            for m in diag["matches"]:
                console.print(f"  - {m}")
        raise typer.Exit(1)

    status_color = {
        "AVAILABLE": "green",
        "BLOCKED_TECHNICAL": "red",
        "BLOCKED_REGULATORY": "yellow",
        "BLOCKED_UNKNOWN": "dim",
    }.get(diag["status"], "white")

    console.print(f"\n[bold]{diag['nudo']}[/bold] — {diag['ccaa']}")
    console.print(f"  Code: {diag['cod_subestacion']}  |  Voltage: {diag['voltage_kv']} kV")
    console.print(f"  Status: [{status_color}]{diag['status']}[/{status_color}]")
    console.print(f"  [dim]{diag['summary']}[/dim]\n")

    # Positions
    pos = diag["positions"]
    pos_str = "  Positions: "
    for key, val in pos.items():
        pos_str += f"{'✓' if val else '·'} {key}  "
    console.print(pos_str)

    # Margins
    console.print("\n  [bold]Technical Margins (MW)[/bold]")
    m = diag["margins"]
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Criterion")
    table.add_column("Capacity", justify="right")
    table.add_column("Margin", justify="right")
    table.add_row("WSCR", f"{m['WSCR']:,}", f"{m['WSCR_margin']:,}")
    table.add_row("Est. Demand", f"{m['Est_Dem']:,}", f"{m['Est_Dem_margin']:,}")
    table.add_row("Est. Storage", f"{m['Est_Alm']:,}", f"{m['Est_Alm_margin']:,}")
    table.add_row("Dynamic 1 (Din1)", "", f"{m['Din1_margin']:,}")
    table.add_row("Dynamic 2 (Din2)", "", f"{m['Din2_margin']:,}")
    console.print(table)

    # Agreement
    console.print(f"\n  Reference value: {diag['valor_referencia']:,} MW")
    console.print(f"  Agreement: {diag['estado_acuerdo']}")

    # Granted / Pending
    console.print(f"  Granted demand (RdT): {diag['otorgada_dem_rdt']:,} MW")
    console.print(f"  Granted storage (RdT): {diag['otorgada_alm_rdt']:,} MW")
    console.print(f"  Pending demand: {diag['pendiente_dem_rdt']:,} MW")
    console.print(f"  Pending storage: {diag['pendiente_alm_rdt']:,} MW")

    # Available
    console.print("\n  [bold]Available Capacity (MW)[/bold]")
    avail_table = Table(show_header=True, box=None, padding=(0, 2))
    avail_table.add_column("Type")
    avail_table.add_column("MW", justify="right", style="green")
    avail_table.add_column("Binding Criterion")
    a = diag["available"]
    b = diag["binding_criteria"]
    avail_table.add_row("CEP CH", f"{a['CEP_CH']:,}", b["CEP_CH"])
    avail_table.add_row("CEP SH", f"{a['CEP_SH']:,}", b["CEP_SH"])
    avail_table.add_row("NO CEP", f"{a['NO_CEP']:,}", b["NO_CEP"])
    avail_table.add_row("Storage CEP", f"{a['Storage_CEP']:,}", b["Storage_CEP"])
    avail_table.add_row("Storage NO CEP", f"{a['Storage_NO_CEP']:,}", b["Storage_NO_CEP"])
    console.print(avail_table)

    # Alerts and flags
    if diag["wscr_alertas"]:
        console.print(f"\n  [yellow]WSCR Alert: {diag['wscr_alertas']}[/yellow]")
    if diag["motivo_no_otorgable"]:
        console.print(f"  [yellow]Non-grantable: {diag['motivo_no_otorgable']}[/yellow]")
    if diag["is_concurso"]:
        console.print("  [yellow]Competitive tender (concurso) node[/yellow]")
    if diag["est_dem_limit_temp"] and diag["est_dem_limit_temp"] not in ("No", ""):
        console.print(f"  [yellow]Config limitation: {diag['est_dem_limit_temp']}[/yellow]")

    # Narrative report
    from capacidad.analysis import generate_report
    console.print("\n[bold]── Report ──[/bold]\n")
    console.print(generate_report(diag))
    console.print()


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
@app.command()
def report(name: str = typer.Argument(..., help="Node name (e.g. 'ABANILLAS 400')")):
    """Narrative report for a node (clean output for piping/sharing)."""
    from capacidad.analysis import diagnose_node, generate_report

    df = _load()
    diag = diagnose_node(df, name)

    if "error" in diag:
        console.print(f"[red]{diag['error']}[/red]")
        if "matches" in diag:
            for m in diag["matches"]:
                console.print(f"  - {m}")
        raise typer.Exit(1)

    console.print(generate_report(diag))


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------
@app.command()
def search(query: str = typer.Argument(..., help="Search query")):
    """Search nodes by name (fuzzy substring match)."""
    from capacidad.analysis import search_nodes

    df = _load()
    results = search_nodes(df, query)

    if results.empty:
        console.print(f"[yellow]No nodes matching '{query}'[/yellow]")
        raise typer.Exit(1)

    table = Table(title=f"Search: '{query}'")
    table.add_column("Node", style="cyan")
    table.add_column("CCAA")
    table.add_column("CEP CH MW", justify="right", style="green")
    table.add_column("NO CEP MW", justify="right")
    table.add_column("kV", justify="right")

    for _, row in results.iterrows():
        table.add_row(
            row["nudo"],
            row["ccaa"],
            f"{int(row['disp_dem_cep_ch']):,}",
            f"{int(row['disp_dem_no_cep']):,}",
            str(int(row["voltage_kv"])) if row["voltage_kv"] else "",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# blocked
# ---------------------------------------------------------------------------
@app.command()
def blocked(
    reason: Optional[str] = typer.Option(
        None, "--reason", "-r",
        help="Filter: 'technical' or 'regulatory'",
    ),
):
    """List blocked nodes (zero CEP CH capacity)."""
    from capacidad.analysis import blocked_nodes

    df = _load()
    result = blocked_nodes(df, reason=reason)

    console.print(f"\n[bold]Blocked nodes: {len(result)}[/bold]")
    if reason:
        console.print(f"  Filter: {reason}\n")

    # Show summary counts
    tech = result["is_blocked_technical"].sum()
    reg = result["is_blocked_regulatory"].sum()
    console.print(f"  Technical blocks:  {tech}")
    console.print(f"  Regulatory blocks: {reg}")
    console.print(f"  Other/unknown:     {len(result) - tech - reg}\n")

    # Show first 30
    table = Table(title="Blocked Nodes (first 30)")
    table.add_column("Node", style="cyan")
    table.add_column("CCAA")
    table.add_column("Binding Criterion")
    table.add_column("Reason")

    for _, row in result.head(30).iterrows():
        table.add_row(
            row["nudo"],
            row["ccaa"],
            row["limitante_dem_cep_ch"] or "-",
            row["motivo_no_otorgable"][:60] if row["motivo_no_otorgable"] else "-",
        )

    console.print(table)
    if len(result) > 30:
        console.print(f"\n  [dim]... and {len(result) - 30} more. Use export for full list.[/dim]")


# ---------------------------------------------------------------------------
# criteria
# ---------------------------------------------------------------------------
@app.command()
def criteria():
    """Show binding criteria distribution for CEP CH demand."""
    from capacidad.analysis import binding_criteria_distribution

    df = _load()
    dist = binding_criteria_distribution(df)

    # Count empty (no criterion reported)
    empty_count = (df["limitante_dem_cep_ch"] == "").sum()

    table = Table(title="Binding Criteria Distribution (CEP CH)")
    table.add_column("Criterion", style="cyan")
    table.add_column("Nodes", justify="right", style="green")
    table.add_column("% of Reported", justify="right")

    total_reported = dist["nodes"].sum()
    for _, row in dist.iterrows():
        pct = f"{100 * row['nodes'] / total_reported:.1f}%"
        table.add_row(row["criterion"], str(row["nodes"]), pct)

    console.print(table)
    console.print(f"\n  Nodes with no criterion reported: {empty_count} (regulatory/other block)")
    console.print(f"  Total nodes with criterion: {total_reported}")
    console.print()


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------
@app.command()
def export(
    fmt: str = typer.Option("all", "--format", "-f",
                             help="Export format: sqlite, json, parquet, or all"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o",
                                                help="Output directory"),
):
    """Export data to SQLite, JSON, and/or Parquet."""
    from capacidad.export import to_json, to_parquet, to_sqlite

    df = _load()
    out = Path(output_dir) if output_dir else DATA_PROCESSED
    out.mkdir(parents=True, exist_ok=True)

    formats = [fmt] if fmt != "all" else ["sqlite", "json", "parquet"]

    for f in formats:
        if f == "sqlite":
            path = to_sqlite(df, out / "capacidad.db")
            console.print(f"  [green]SQLite:[/green] {path}")
        elif f == "json":
            path = to_json(df, out / "capacidad.json")
            console.print(f"  [green]JSON:[/green]   {path}")
        elif f == "parquet":
            path = to_parquet(df, out / "capacidad.parquet")
            console.print(f"  [green]Parquet:[/green] {path}")
        else:
            console.print(f"[red]Unknown format: {f}[/red]")


# ---------------------------------------------------------------------------
# dashboard
# ---------------------------------------------------------------------------
@app.command()
def dashboard():
    """Launch Streamlit web dashboard."""
    dashboard_path = Path(__file__).parent / "dashboard.py"
    console.print("[blue]Launching Streamlit dashboard...[/blue]")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(dashboard_path)],
    )


if __name__ == "__main__":
    app()
