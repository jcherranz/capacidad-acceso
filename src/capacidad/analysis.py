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
    """Generate a prose narrative report from a diagnose_node() result.

    Returns a human-readable multi-line string suitable for terminal or markdown.
    """
    if "error" in diag:
        return f"Error: {diag['error']}"

    # Plain-English lookup for criterion codes
    criterion_names = {
        "WSCR_Nudo": "WSCR (short-circuit ratio) at this node",
        "WSCR_Zona": "WSCR (short-circuit ratio) in the surrounding zone",
        "Est_Dem_Nudo": "steady-state demand capacity at this node",
        "Est_Dem_Zona": "steady-state demand capacity in the surrounding zone",
        "Est_Alm_Nudo": "steady-state storage capacity at this node",
        "Est_Alm_Zona": "steady-state storage capacity in the surrounding zone",
        "Din1_Zona": "transient stability (dynamic criterion 1) in the zone",
        "Din2_Zona": "transient stability (dynamic criterion 2) in the zone",
    }

    # Helpers
    def _crit(code: str) -> str:
        if not code:
            return "not reported"
        if "/" in code:
            parts = [criterion_names.get(p.strip(), p.strip()) for p in code.split("/")]
            return " combined with ".join(parts)
        return criterion_names.get(code, code)

    def _mw(val: int) -> str:
        return f"{val:,} MW"

    nudo = diag["nudo"]
    ccaa = diag["ccaa"]
    voltage = int(diag["voltage_kv"])
    avail = diag["available"]
    bind = diag["binding_criteria"]
    margins = diag["margins"]
    status = diag["status"]

    lines: list[str] = []

    # Header
    lines.append(f"{nudo} — {ccaa} ({voltage} kV)")
    lines.append("")

    # Paragraph 1: availability summary
    cep_ch = avail["CEP_CH"]
    no_cep = avail["NO_CEP"]
    storage_cep = avail["Storage_CEP"]

    if status == "AVAILABLE":
        lines.append(
            f"This node has {_mw(cep_ch)} available for new power-electronics "
            f"demand (CEP CH) and {_mw(no_cep)} for conventional demand."
        )
    elif status == "BLOCKED_TECHNICAL":
        lines.append(
            f"This node is technically blocked — no capacity is available "
            f"for new power-electronics demand (CEP CH)."
        )
        criterion = bind.get("CEP_CH", "")
        lines.append(
            f"The binding constraint is {_crit(criterion)}, which has "
            f"reached its limit at this connection point."
        )
        if no_cep > 0:
            lines.append(
                f"However, {_mw(no_cep)} remains available for conventional "
                f"demand (NO CEP), which is not subject to this constraint."
            )
    elif status == "BLOCKED_REGULATORY":
        lines.append(
            f"This node is blocked for regulatory reasons: "
            f"{diag['motivo_no_otorgable']}."
        )
    else:
        lines.append(
            "This node is blocked. No technical criterion or regulatory "
            "reason has been reported for the block."
        )

    lines.append("")

    # Paragraph 2: binding criteria detail (only for available nodes)
    if status == "AVAILABLE":
        cep_ch_crit = bind.get("CEP_CH", "")
        no_cep_crit = bind.get("NO_CEP", "")
        storage_crit = bind.get("Storage_CEP", "")

        lines.append(
            f"The binding constraint for power-electronics demand is "
            f"{_crit(cep_ch_crit)}. "
            f"Conventional demand is limited to {_mw(no_cep)} by "
            f"{_crit(no_cep_crit)}. "
            f"Storage capacity is {_mw(storage_cep)}"
            + (f", limited by {_crit(storage_crit)}." if storage_crit else ".")
        )
        lines.append("")

    # Paragraph 3: granted, pending, agreement
    granted_dem = diag["otorgada_dem_rdt"]
    granted_alm = diag["otorgada_alm_rdt"]
    pending_dem = diag["pendiente_dem_rdt"]
    pending_alm = diag["pendiente_alm_rdt"]

    has_granted = granted_dem > 0 or granted_alm > 0
    has_pending = pending_dem > 0 or pending_alm > 0

    if has_granted or has_pending:
        parts = []
        if granted_dem > 0:
            parts.append(f"{_mw(granted_dem)} of demand has been granted")
        if granted_alm > 0:
            parts.append(f"{_mw(granted_alm)} of storage has been granted")
        if pending_dem > 0:
            parts.append(f"{_mw(pending_dem)} of demand is pending")
        if pending_alm > 0:
            parts.append(f"{_mw(pending_alm)} of storage is pending")
        lines.append(", and ".join(parts) + " at this node.")
    else:
        lines.append(
            "No demand has been granted or is pending at this node."
        )

    # Agreement
    acuerdo = diag["estado_acuerdo"]
    ref_val = diag["valor_referencia"]
    if acuerdo == "SI":
        lines.append(
            f"The reference value agreement is in place ({_mw(ref_val)})."
        )
    elif acuerdo == "NO":
        lines.append(
            f"The reference value agreement has NOT been reached "
            f"({_mw(ref_val)} reference value)."
        )
    else:
        lines.append(
            "The reference value agreement is not applicable "
            "(no distribution interface)."
        )

    # Concurso
    if diag["is_concurso"]:
        lines.append("This node is subject to competitive tender (concurso).")
    else:
        lines.append("This node is not subject to competitive tender.")

    lines.append("")

    # Paragraph 4: alerts and limitations
    alerts = []
    if diag["wscr_alertas"]:
        alerts.append(f"WSCR security alert: {diag['wscr_alertas']}.")
    else:
        alerts.append("No WSCR security alerts.")

    limit_temp = diag.get("est_dem_limit_temp", "")
    if limit_temp and limit_temp not in ("No", ""):
        alerts.append(f"Substation configuration limitation: {limit_temp}.")
    else:
        alerts.append("No substation configuration limitations.")

    lines.append(" ".join(alerts))

    return "\n".join(lines)


def search_nodes(df: pd.DataFrame, query: str, limit: int = 20) -> pd.DataFrame:
    """Search nodes by name (case-insensitive substring match)."""
    mask = df["nudo"].str.contains(query, case=False, na=False)
    cols = ["nudo", "ccaa", "disp_dem_cep_ch", "disp_dem_no_cep", "voltage_kv"]
    return df[mask][cols].head(limit).reset_index(drop=True)
