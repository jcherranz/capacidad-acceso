"""Filter, aggregate, and diagnostic functions for REE capacity data."""

import pandas as pd

from capacidad.models import AVAILABLE_CAPACITY_COLUMNS, BINDING_CRITERIA_COLUMNS


def filter_nodes(
    df: pd.DataFrame,
    ccaa: str | None = None,
    min_mw: float = 0,
    capacity_col: str = "disp_dem_cep_ch",
    voltage_kv: float | None = None,
    only_available: bool = False,
    only_concurso: bool | None = None,
) -> pd.DataFrame:
    """Filter nodes by region, capacity, voltage, etc."""
    mask = pd.Series(True, index=df.index)

    if ccaa:
        mask &= df["ccaa"].str.contains(ccaa, case=False, na=False)
    if min_mw > 0:
        mask &= df[capacity_col] >= min_mw
    if voltage_kv is not None:
        mask &= df["voltage_kv"] == voltage_kv
    if only_available:
        mask &= df[capacity_col] > 0
    if only_concurso is not None:
        mask &= df["is_concurso"] == only_concurso

    return df[mask].copy()


def summary_by_region(
    df: pd.DataFrame,
    capacity_col: str = "disp_dem_cep_ch",
) -> pd.DataFrame:
    """Aggregate capacity statistics by Autonomous Community."""
    grouped = df.groupby("ccaa").agg(
        nodes=("nudo", "count"),
        total_mw=(capacity_col, "sum"),
        avg_mw=(capacity_col, "mean"),
        nodes_with_capacity=(capacity_col, lambda x: (x > 0).sum()),
        nodes_blocked=(capacity_col, lambda x: (x == 0).sum()),
        unresolved_agreement=("estado_acuerdo", lambda x: (x == "NO").sum()),
    )
    grouped = grouped.sort_values("total_mw", ascending=False)
    grouped["total_mw"] = grouped["total_mw"].astype(int)
    grouped["avg_mw"] = grouped["avg_mw"].round(0).astype(int)
    return grouped.reset_index()


def top_nodes(
    df: pd.DataFrame,
    n: int = 20,
    capacity_col: str = "disp_dem_cep_ch",
) -> pd.DataFrame:
    """Return top N nodes by available capacity."""
    cols = ["nudo", "ccaa", capacity_col, "limitante_dem_cep_ch",
            "voltage_kv", "is_concurso"]
    return (
        df[df[capacity_col] > 0][cols]
        .sort_values(capacity_col, ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def diagnose_node(df: pd.DataFrame, node_name: str) -> dict:
    """Full diagnostic for a specific node.

    Returns a dict with all relevant fields and interpretation.
    """
    matches = df[df["nudo"].str.upper() == node_name.upper()]
    if matches.empty:
        # Try fuzzy match
        matches = df[df["nudo"].str.contains(node_name, case=False, na=False)]
        if matches.empty:
            return {"error": f"Node '{node_name}' not found"}
        if len(matches) > 1:
            return {
                "error": f"Multiple matches for '{node_name}'",
                "matches": matches["nudo"].tolist(),
            }

    row = matches.iloc[0]
    diag = {
        "nudo": row["nudo"],
        "ccaa": row["ccaa"],
        "cod_subestacion": row["cod_subestacion"],
        "voltage_kv": row["voltage_kv"],
        # Physical positions
        "has_demand_bay": row["has_demand_bay"],
        "positions": {
            "gen_E": row["pos_gen_E"], "gen_P": row["pos_gen_P"],
            "con_E": row["pos_con_E"], "con_P": row["pos_con_P"],
            "dist_E": row["pos_dist_E"], "dist_P": row["pos_dist_P"],
        },
        # Technical criteria margins
        "margins": {
            "WSCR": int(row["wscr_cap_nodal"]),
            "WSCR_margin": int(row["wscr_margen"]),
            "Est_Dem": int(row["est_dem_cap_nodal"]),
            "Est_Dem_margin": int(row["est_dem_margen"]),
            "Est_Alm": int(row["est_alm_cap_nodal"]),
            "Est_Alm_margin": int(row["est_alm_margen"]),
            "Din1_margin": int(row["din1_margen"]),
            "Din2_margin": int(row["din2_margen"]),
        },
        # WSCR details
        "wscr_binudos": row["wscr_binudos"],
        "wscr_alertas": row["wscr_alertas"],
        # Agreement
        "valor_referencia": int(row["valor_referencia"]),
        "estado_acuerdo": row["estado_acuerdo"],
        # Granted
        "otorgada_dem_rdt": int(row["otorgada_dem_rdt"]),
        "otorgada_alm_rdt": int(row["otorgada_alm_rdt"]),
        # Pending
        "pendiente_dem_rdt": int(row["pendiente_dem_rdt"]),
        "pendiente_alm_rdt": int(row["pendiente_alm_rdt"]),
        # Available capacity
        "available": {
            "CEP_CH": int(row["disp_dem_cep_ch"]),
            "CEP_SH": int(row["disp_dem_cep_sh"]),
            "NO_CEP": int(row["disp_dem_no_cep"]),
            "Storage_CEP": int(row["disp_alm_cep"]),
            "Storage_NO_CEP": int(row["disp_alm_no_cep"]),
        },
        # Binding criteria
        "binding_criteria": {
            "CEP_CH": row["limitante_dem_cep_ch"],
            "CEP_SH": row["limitante_dem_cep_sh"],
            "NO_CEP": row["limitante_dem_no_cep"],
            "Storage_CEP": row["limitante_alm_cep"],
            "Storage_NO_CEP": row["limitante_alm_no_cep"],
        },
        # Non-grantable
        "non_grantable": {
            "CEP_CH": int(row["no_otorg_dem_cep_ch"]),
            "NO_CEP": int(row["no_otorg_dem_no_cep"]),
        },
        "motivo_no_otorgable": row["motivo_no_otorgable"],
        # Flags
        "is_concurso": row["is_concurso"],
        "est_dem_limit_temp": row["est_dem_limit_temp"],
    }

    # Interpretation
    cep_ch = diag["available"]["CEP_CH"]
    if cep_ch > 0:
        diag["status"] = "AVAILABLE"
        diag["summary"] = f"{cep_ch} MW available for CEP CH demand"
    elif diag["binding_criteria"]["CEP_CH"]:
        diag["status"] = "BLOCKED_TECHNICAL"
        diag["summary"] = (
            f"Technically blocked by {diag['binding_criteria']['CEP_CH']}"
        )
    elif diag["motivo_no_otorgable"]:
        diag["status"] = "BLOCKED_REGULATORY"
        diag["summary"] = f"Regulatory block: {diag['motivo_no_otorgable']}"
    else:
        diag["status"] = "BLOCKED_UNKNOWN"
        diag["summary"] = "Blocked — no criteria or regulatory reason reported"

    return diag


def blocked_nodes(
    df: pd.DataFrame,
    reason: str | None = None,
) -> pd.DataFrame:
    """List nodes with zero available capacity, grouped by block reason.

    Args:
        reason: Filter by 'technical', 'regulatory', or None for all.
    """
    blocked = df[df["disp_dem_cep_ch"] == 0].copy()

    if reason == "technical":
        blocked = blocked[blocked["is_blocked_technical"]]
    elif reason == "regulatory":
        blocked = blocked[blocked["is_blocked_regulatory"]]

    cols = ["nudo", "ccaa", "limitante_dem_cep_ch", "motivo_no_otorgable",
            "is_blocked_technical", "is_blocked_regulatory"]
    return blocked[cols].sort_values("ccaa").reset_index(drop=True)


def binding_criteria_distribution(
    df: pd.DataFrame,
    criteria_col: str = "limitante_dem_cep_ch",
) -> pd.DataFrame:
    """Count nodes by binding criterion."""
    counts = (
        df[df[criteria_col] != ""][criteria_col]
        .value_counts()
        .reset_index()
    )
    counts.columns = ["criterion", "nodes"]
    return counts


def generate_report(diag: dict) -> str:
    """Generate a structured markdown report from a diagnose_node() result.

    Returns a human-readable multi-line string with bullets, a summary table,
    criterion explanations, and all available diagnostic data.
    """
    if "error" in diag:
        return f"Error: {diag['error']}"

    # --- Criterion context: what it means + what could resolve it -----------
    _criterion_context = {
        "WSCR": (
            "Not enough synchronous generation nearby to anchor voltage — "
            "the grid is electrically \"weak\" at this point. "
            "Synchronous condensers, grid-forming inverters, or new "
            "synchronous generation could lift this limit."
        ),
        "Est_Dem": (
            "Thermal capacity of lines or transformers serving demand is "
            "exhausted. Grid reinforcement (new lines, transformer upgrades) "
            "would be needed to increase headroom."
        ),
        "Est_Alm": (
            "Thermal capacity of lines or transformers serving storage "
            "connections is exhausted. Grid reinforcement (new lines, "
            "transformer upgrades) would be needed."
        ),
        "Din1": (
            "The zone cannot absorb more load without risking oscillatory "
            "instability after a fault. Generation closer to load or network "
            "reinforcement for damping could help."
        ),
        "Din2": (
            "Voltage recovery after faults is too slow in this zone. "
            "Reactive compensation or additional synchronous machines "
            "could improve recovery."
        ),
    }

    # Human-readable criterion names
    _criterion_names = {
        "WSCR_Nudo": "WSCR (short-circuit ratio) at this node",
        "WSCR_Zona": "WSCR (short-circuit ratio) in the surrounding zone",
        "Est_Dem_Nudo": "steady-state demand capacity at this node",
        "Est_Dem_Zona": "steady-state demand capacity in the surrounding zone",
        "Est_Alm_Nudo": "steady-state storage capacity at this node",
        "Est_Alm_Zona": "steady-state storage capacity in the surrounding zone",
        "Din1_Zona": "transient stability (dynamic criterion 1) in the zone",
        "Din2_Zona": "transient stability (dynamic criterion 2) in the zone",
    }

    # --- Helpers -----------------------------------------------------------
    def _mw(val: int) -> str:
        return f"{val:,} MW"

    def _crit_name(code: str) -> str:
        if not code:
            return "not reported"
        if "/" in code:
            parts = [_criterion_names.get(p.strip(), p.strip())
                     for p in code.split("/")]
            return " combined with ".join(parts)
        return _criterion_names.get(code, code)

    def _margin_for_criterion(code: str, margins: dict) -> str:
        """Map a binding criterion code to the corresponding margin value."""
        if not code:
            return "—"
        # For combined criteria (e.g. "Est_Dem_Nudo/Din1_Zona"), use the
        # minimum margin across the referenced criteria.
        codes = [c.strip() for c in code.split("/")] if "/" in code else [code]
        values = []
        for c in codes:
            prefix = c.split("_")[0]  # WSCR, Est, Din1, Din2
            if c.startswith("WSCR"):
                values.append(margins.get("WSCR_margin", 0))
            elif c.startswith("Est_Dem"):
                values.append(margins.get("Est_Dem_margin", 0))
            elif c.startswith("Est_Alm"):
                values.append(margins.get("Est_Alm_margin", 0))
            elif c.startswith("Din1"):
                values.append(margins.get("Din1_margin", 0))
            elif c.startswith("Din2"):
                values.append(margins.get("Din2_margin", 0))
        if values:
            return f"{min(values):,}"
        return "—"

    def _criterion_explanation(code: str) -> str:
        """Build a 2-3 sentence explanation for a criterion code."""
        if not code:
            return ""
        codes = [c.strip() for c in code.split("/")] if "/" in code else [code]
        prefixes = []
        for c in codes:
            # Extract prefix: WSCR, Est_Dem, Est_Alm, Din1, Din2
            if c.startswith("WSCR"):
                prefixes.append("WSCR")
            elif c.startswith("Est_Dem"):
                prefixes.append("Est_Dem")
            elif c.startswith("Est_Alm"):
                prefixes.append("Est_Alm")
            elif c.startswith("Din1"):
                prefixes.append("Din1")
            elif c.startswith("Din2"):
                prefixes.append("Din2")
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for p in prefixes:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        parts = [_criterion_context[p] for p in unique if p in _criterion_context]
        return " ".join(parts)

    # --- Unpack diag -------------------------------------------------------
    nudo = diag["nudo"]
    ccaa = diag["ccaa"]
    voltage = int(diag["voltage_kv"])
    cod_sub = diag.get("cod_subestacion", "")
    avail = diag["available"]
    bind = diag["binding_criteria"]
    margins = diag["margins"]
    status = diag["status"]
    positions = diag["positions"]

    lines: list[str] = []

    # === 1. Header =========================================================
    header = f"## {nudo} — {ccaa} ({voltage} kV)"
    if cod_sub:
        header += f"  \nSubstation code: {cod_sub}"
    lines.append(header)
    lines.append("")

    # === 2. Status table ===================================================
    # Define rows: (label, avail_key, bind_key)
    cap_rows = [
        ("CEP CH demand", "CEP_CH", "CEP_CH"),
        ("CEP SH demand", "CEP_SH", "CEP_SH"),
        ("NO CEP demand", "NO_CEP", "NO_CEP"),
        ("CEP storage", "Storage_CEP", "Storage_CEP"),
        ("NO CEP storage", "Storage_NO_CEP", "Storage_NO_CEP"),
    ]

    lines.append("| Type | Available (MW) | Binding criterion | Margin (MW) |")
    lines.append("|------|---------------:|-------------------|------------:|")
    for label, akey, bkey in cap_rows:
        mw = avail[akey]
        crit = bind.get(bkey, "")
        margin = _margin_for_criterion(crit, margins)
        crit_display = crit if crit else "—"
        lines.append(f"| {label} | {mw:,} | {crit_display} | {margin} |")
    lines.append("")

    # === 3. Why this limit? ================================================
    primary_crit = bind.get("CEP_CH", "")
    explanation = _criterion_explanation(primary_crit)
    if explanation:
        lines.append("### Why this limit?")
        lines.append("")
        lines.append(
            f"The binding criterion for CEP CH demand is "
            f"**{_crit_name(primary_crit)}**."
        )
        lines.append("")
        lines.append(explanation)
        lines.append("")

    # === 4. Grid connection ================================================
    bay_labels = {
        "gen_E": "Generation/storage bay (existing)",
        "gen_P": "Generation/storage bay (planned)",
        "con_E": "Demand bay (existing)",
        "con_P": "Demand bay (planned)",
        "dist_E": "Distribution connection (existing)",
        "dist_P": "Distribution connection (planned)",
    }
    bay_bullets = []
    for key, label in bay_labels.items():
        if positions.get(key):
            bay_bullets.append(f"- {label}: yes")
    if not diag["has_demand_bay"]:
        bay_bullets.append("- **No demand bay** — physical connection needed")

    if bay_bullets:
        lines.append("### Grid connection")
        lines.append("")
        lines.extend(bay_bullets)
        lines.append("")

    # === 5. Granted & pending ==============================================
    gp_bullets = []
    if diag["otorgada_dem_rdt"] > 0:
        gp_bullets.append(
            f"- Granted demand (RdT): {_mw(diag['otorgada_dem_rdt'])}")
    if diag["otorgada_alm_rdt"] > 0:
        gp_bullets.append(
            f"- Granted storage (RdT): {_mw(diag['otorgada_alm_rdt'])}")
    if diag["pendiente_dem_rdt"] > 0:
        gp_bullets.append(
            f"- Pending demand: {_mw(diag['pendiente_dem_rdt'])}")
    if diag["pendiente_alm_rdt"] > 0:
        gp_bullets.append(
            f"- Pending storage: {_mw(diag['pendiente_alm_rdt'])}")

    if gp_bullets:
        lines.append("### Granted & pending")
        lines.append("")
        lines.extend(gp_bullets)
        lines.append("")

    # === 6. Administrative =================================================
    admin_bullets = []

    # Reference value + agreement
    ref_val = diag["valor_referencia"]
    acuerdo = diag["estado_acuerdo"]
    if acuerdo == "SI":
        admin_bullets.append(
            f"- Reference value: {_mw(ref_val)} — agreement **reached**")
    elif acuerdo == "NO":
        admin_bullets.append(
            f"- Reference value: {_mw(ref_val)} — agreement **NOT reached**")
    else:
        admin_bullets.append(
            "- Reference value agreement: N/A (no distribution interface)")

    # Concurso
    if diag["is_concurso"]:
        admin_bullets.append("- Subject to **competitive tender** (concurso)")

    # Non-grantable
    ng = diag["non_grantable"]
    motivo = diag.get("motivo_no_otorgable", "")
    ng_items = []
    if ng.get("CEP_CH", 0) > 0:
        ng_items.append(f"CEP CH: {_mw(ng['CEP_CH'])}")
    if ng.get("NO_CEP", 0) > 0:
        ng_items.append(f"NO CEP: {_mw(ng['NO_CEP'])}")
    if ng_items:
        reason = f" — {motivo}" if motivo else ""
        admin_bullets.append(
            f"- Non-grantable: {', '.join(ng_items)}{reason}")

    lines.append("### Administrative")
    lines.append("")
    lines.extend(admin_bullets)
    lines.append("")

    # === 7. Alerts (only if something to report) ===========================
    alert_bullets = []
    wscr_alertas = diag.get("wscr_alertas", "")
    wscr_binudos = diag.get("wscr_binudos", "")
    # Treat "N/A" as empty
    if wscr_alertas and wscr_alertas != "N/A":
        bullet = f"- WSCR alert: {wscr_alertas}"
        if wscr_binudos and wscr_binudos != "N/A":
            bullet += f" (shared with {wscr_binudos})"
        alert_bullets.append(bullet)
    elif wscr_binudos and wscr_binudos != "N/A":
        alert_bullets.append(
            f"- WSCR shared node: {wscr_binudos}")

    limit_temp = diag.get("est_dem_limit_temp", "")
    if limit_temp and limit_temp not in ("No", ""):
        alert_bullets.append(
            f"- Configuration limitation: {limit_temp}")

    if alert_bullets:
        lines.append("### Alerts")
        lines.append("")
        lines.extend(alert_bullets)
        lines.append("")

    return "\n".join(lines)


def search_nodes(df: pd.DataFrame, query: str, limit: int = 20) -> pd.DataFrame:
    """Search nodes by name (case-insensitive substring match)."""
    mask = df["nudo"].str.contains(query, case=False, na=False)
    cols = ["nudo", "ccaa", "disp_dem_cep_ch", "disp_dem_no_cep", "voltage_kv"]
    return df[mask][cols].head(limit).reset_index(drop=True)
