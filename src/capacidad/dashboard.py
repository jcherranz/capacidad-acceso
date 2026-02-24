"""Streamlit web dashboard for REE demand access capacity data."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from capacidad.parser import load_csv
from capacidad.analysis import (
    summary_by_region,
    top_nodes,
    diagnose_node,
    generate_report,
    binding_criteria_distribution,
    filter_nodes,
    search_nodes,
)

st.set_page_config(
    page_title="REE Demand Access Capacity",
    page_icon="⚡",
    layout="wide",
)

# ── Fira Code minimal theme ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600&display=swap');

html, body, [class*="st-"] {
    font-family: 'Fira Code', monospace;
}

/* headers */
h1, h2, h3, .stTabs [data-baseweb="tab"] {
    font-family: 'Fira Code', monospace;
    font-weight: 500;
    letter-spacing: -0.02em;
}
h1 { font-size: 1.5rem; color: #c0caf5; }
h2 { font-size: 1.2rem; color: #a9b1d6; }
h3 { font-size: 1.05rem; color: #9aa5ce; }

/* sidebar */
section[data-testid="stSidebar"] {
    background-color: #16161e;
    border-right: 1px solid #292e42;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stNumberInput label {
    font-size: 0.8rem;
    color: #565f89;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* metrics */
[data-testid="stMetric"] {
    background: #16161e;
    border: 1px solid #292e42;
    border-radius: 6px;
    padding: 0.8rem 1rem;
}
[data-testid="stMetricValue"] {
    font-size: 1.4rem;
    font-weight: 600;
    color: #7aa2f7;
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem;
    color: #565f89;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #292e42;
}
.stTabs [data-baseweb="tab"] {
    font-size: 0.85rem;
    color: #565f89;
    padding: 0.6rem 1.2rem;
    border: none;
    background: transparent;
}
.stTabs [aria-selected="true"] {
    color: #7aa2f7;
    border-bottom: 2px solid #7aa2f7;
    background: transparent;
}

/* dataframes */
.stDataFrame { font-size: 0.8rem; }

/* dividers */
hr { border-color: #292e42; opacity: 0.5; }

/* inputs */
.stTextInput input, .stSelectbox [data-baseweb="select"],
.stNumberInput input {
    font-family: 'Fira Code', monospace;
    font-size: 0.85rem;
    background: #16161e;
    border-color: #292e42;
    color: #a9b1d6;
}

/* report text */
.stMarkdown p { line-height: 1.6; font-size: 0.88rem; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def get_data():
    return load_csv()


df = get_data()

# ── Sidebar Filters ──────────────────────────────────────────────────────────
st.sidebar.title("Filters")

ccaa_options = ["All"] + sorted(df["ccaa"].unique().tolist())
selected_ccaa = st.sidebar.selectbox("Autonomous Community", ccaa_options)

capacity_options = {
    "CEP CH Demand": "disp_dem_cep_ch",
    "CEP SH Demand": "disp_dem_cep_sh",
    "NO CEP Demand": "disp_dem_no_cep",
    "CEP Storage": "disp_alm_cep",
    "NO CEP Storage": "disp_alm_no_cep",
}
selected_cap_label = st.sidebar.selectbox("Capacity Type", list(capacity_options.keys()))
cap_col = capacity_options[selected_cap_label]

min_mw = st.sidebar.number_input("Minimum MW", min_value=0, value=0, step=50)

voltage_options = ["All"] + sorted(
    [int(v) for v in df["voltage_kv"].dropna().unique()]
)
selected_voltage = st.sidebar.selectbox("Voltage (kV)", voltage_options)

# Apply filters
filtered = df.copy()
if selected_ccaa != "All":
    filtered = filtered[filtered["ccaa"] == selected_ccaa]
if min_mw > 0:
    filtered = filtered[filtered[cap_col] >= min_mw]
if selected_voltage != "All":
    filtered = filtered[filtered["voltage_kv"] == float(selected_voltage)]

st.sidebar.markdown("---")
st.sidebar.metric("Filtered Nodes", len(filtered))
st.sidebar.metric("Total MW", f"{int(filtered[cap_col].sum()):,}")

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview", "Node Explorer", "Criteria Analysis", "Data Center Focus"
])

# ── Tab 1: Overview ──────────────────────────────────────────────────────────
with tab1:
    st.header("Network Overview")

    # KPIs
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Nodes", f"{len(filtered):,}")
    col2.metric(
        "Available Nodes",
        f"{(filtered[cap_col] > 0).sum():,}",
    )
    col3.metric(
        "Total MW",
        f"{int(filtered[cap_col].sum()):,}",
    )
    col4.metric(
        "Concurso Nodes",
        f"{filtered['is_concurso'].sum():,}",
    )
    col5.metric(
        "Unresolved Agreements",
        f"{(filtered['estado_acuerdo'] == 'NO').sum():,}",
    )

    st.markdown("---")

    # Regional bar chart
    summary = summary_by_region(filtered, capacity_col=cap_col)

    fig = px.bar(
        summary,
        x="ccaa",
        y="total_mw",
        color="total_mw",
        color_continuous_scale=[[0, "#292e42"], [1, "#7aa2f7"]],
        title=f"Available {selected_cap_label} by Region (MW)",
        labels={"ccaa": "Autonomous Community", "total_mw": "MW"},
    )
    fig.update_layout(
        xaxis_tickangle=-45, showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Fira Code, monospace", color="#a9b1d6", size=11),
        xaxis=dict(gridcolor="#292e42"), yaxis=dict(gridcolor="#292e42"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Nodes with vs without capacity
    col_a, col_b = st.columns(2)
    with col_a:
        avail_count = (filtered[cap_col] > 0).sum()
        blocked_count = (filtered[cap_col] == 0).sum()
        fig_pie = px.pie(
            names=["Available", "Blocked"],
            values=[avail_count, blocked_count],
            title="Node Availability",
            color_discrete_sequence=["#7aa2f7", "#414868"],
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Fira Code, monospace", color="#a9b1d6", size=11),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_b:
        # Agreement status
        acuerdo_counts = filtered["estado_acuerdo"].value_counts()
        fig_acuerdo = px.pie(
            names=acuerdo_counts.index,
            values=acuerdo_counts.values,
            title="Agreement Status (Valor de Referencia)",
            color_discrete_map={"SI": "#9ece6a", "NO": "#f7768e", "N/A": "#414868"},
        )
        fig_acuerdo.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Fira Code, monospace", color="#a9b1d6", size=11),
        )
        st.plotly_chart(fig_acuerdo, use_container_width=True)

# ── Tab 2: Node Explorer ─────────────────────────────────────────────────────
with tab2:
    st.header("Node Explorer")

    search_query = st.text_input("Search node by name", "")

    if search_query:
        results = search_nodes(filtered, search_query, limit=50)
        st.dataframe(results, use_container_width=True)
    else:
        # Show top nodes table
        display_cols = [
            "nudo", "ccaa", "voltage_kv",
            "disp_dem_cep_ch", "disp_dem_no_cep", "disp_alm_cep",
            "limitante_dem_cep_ch", "estado_acuerdo", "is_concurso",
        ]
        st.dataframe(
            filtered[display_cols]
            .sort_values(cap_col, ascending=False)
            .head(100),
            use_container_width=True,
        )

    st.markdown("---")

    # Node diagnostic
    st.subheader("Node Diagnostic")
    node_name = st.text_input("Enter exact node name (e.g., 'ABANILLAS 400')", "")
    if node_name:
        diag = diagnose_node(df, node_name)
        if "error" in diag:
            st.error(diag["error"])
            if "matches" in diag:
                st.write("Did you mean:", diag["matches"])
        else:
            status_emoji = {
                "AVAILABLE": "🟢",
                "BLOCKED_TECHNICAL": "🔴",
                "BLOCKED_REGULATORY": "🟡",
                "BLOCKED_UNKNOWN": "⚪",
            }
            emoji = status_emoji.get(diag["status"], "⚪")
            st.markdown(f"### {emoji} {diag['nudo']} — {diag['ccaa']}")
            st.markdown(generate_report(diag))

# ── Tab 3: Criteria Analysis ─────────────────────────────────────────────────
with tab3:
    st.header("Binding Criteria Analysis")

    dist = binding_criteria_distribution(filtered)
    empty_count = (filtered["limitante_dem_cep_ch"] == "").sum()

    fig_crit = px.bar(
        dist,
        x="criterion",
        y="nodes",
        color="nodes",
        color_continuous_scale=[[0, "#292e42"], [1, "#f7768e"]],
        title="Binding Criteria Distribution (CEP CH Demand)",
        labels={"criterion": "Criterion", "nodes": "Node Count"},
    )
    fig_crit.update_layout(
        xaxis_tickangle=-45, showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Fira Code, monospace", color="#a9b1d6", size=11),
        xaxis=dict(gridcolor="#292e42"), yaxis=dict(gridcolor="#292e42"),
    )
    st.plotly_chart(fig_crit, use_container_width=True)

    st.metric(
        "Nodes with no criterion (regulatory block)",
        f"{empty_count}",
    )

    st.markdown("---")

    # Regulatory vs Technical blocks
    st.subheader("Block Breakdown")
    tech_blocked = filtered["is_blocked_technical"].sum()
    reg_blocked = filtered["is_blocked_regulatory"].sum()
    both_blocked = (filtered["is_blocked_technical"] & filtered["is_blocked_regulatory"]).sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Technical Blocks", int(tech_blocked))
    c2.metric("Regulatory Blocks", int(reg_blocked))
    c3.metric("Both", int(both_blocked))

    # Motivo breakdown
    st.subheader("Non-Grantable Reasons")
    motivo_counts = (
        filtered[filtered["motivo_no_otorgable"] != ""]["motivo_no_otorgable"]
        .value_counts()
        .reset_index()
    )
    motivo_counts.columns = ["reason", "count"]
    if not motivo_counts.empty:
        fig_motivo = px.bar(
            motivo_counts.head(10),
            x="count",
            y="reason",
            orientation="h",
            title="Non-Grantable Reasons",
            labels={"reason": "", "count": "Nodes"},
            color_discrete_sequence=["#e0af68"],
        )
        fig_motivo.update_layout(
            yaxis={"autorange": "reversed"},
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Fira Code, monospace", color="#a9b1d6", size=11),
            xaxis=dict(gridcolor="#292e42"), yaxis=dict(gridcolor="#292e42"),
        )
        st.plotly_chart(fig_motivo, use_container_width=True)

# ── Tab 4: Data Center Focus ─────────────────────────────────────────────────
with tab4:
    st.header("Data Center Focus (CEP CH)")
    st.markdown(
        "CEP CH capacity is the key metric for data centers, electrolysers, "
        "and modern industrial loads that use power electronics."
    )

    # Best nodes for data centers
    cep_ch_nodes = filtered[filtered["disp_dem_cep_ch"] > 0].sort_values(
        "disp_dem_cep_ch", ascending=False
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Nodes with CEP CH > 0", len(cep_ch_nodes))
    c2.metric("Total CEP CH MW", f"{int(cep_ch_nodes['disp_dem_cep_ch'].sum()):,}")
    c3.metric(
        "Avg CEP CH per node",
        f"{int(cep_ch_nodes['disp_dem_cep_ch'].mean()):,}" if len(cep_ch_nodes) > 0 else "0",
    )

    st.subheader("Best Nodes for Data Centers")
    dc_cols = [
        "nudo", "ccaa", "voltage_kv", "disp_dem_cep_ch",
        "limitante_dem_cep_ch", "wscr_alertas",
        "has_demand_bay", "is_concurso", "estado_acuerdo",
    ]
    st.dataframe(cep_ch_nodes[dc_cols].head(50), use_container_width=True)

    st.markdown("---")

    # WSCR alerts on available nodes
    st.subheader("WSCR Risk on Available Nodes")
    wscr_risk = cep_ch_nodes[cep_ch_nodes["has_wscr_alert"]]
    if len(wscr_risk) > 0:
        st.warning(f"{len(wscr_risk)} available nodes have WSCR security alerts")
        st.dataframe(
            wscr_risk[["nudo", "ccaa", "disp_dem_cep_ch", "wscr_alertas"]],
            use_container_width=True,
        )
    else:
        st.success("No WSCR alerts on available nodes in current filter")

    st.markdown("---")

    # CEP vs NO CEP comparison
    st.subheader("CEP vs NO CEP Capacity Comparison")
    comparison = filtered[
        (filtered["disp_dem_cep_ch"] > 0) | (filtered["disp_dem_no_cep"] > 0)
    ][["nudo", "ccaa", "disp_dem_cep_ch", "disp_dem_no_cep"]].copy()
    comparison["wscr_penalty"] = comparison["disp_dem_no_cep"] - comparison["disp_dem_cep_ch"]

    fig_scatter = px.scatter(
        comparison,
        x="disp_dem_no_cep",
        y="disp_dem_cep_ch",
        hover_data=["nudo", "ccaa"],
        title="CEP CH vs NO CEP Demand Capacity (per node)",
        labels={
            "disp_dem_no_cep": "NO CEP Demand (MW)",
            "disp_dem_cep_ch": "CEP CH Demand (MW)",
        },
        color_discrete_sequence=["#7aa2f7"],
    )
    fig_scatter.add_shape(
        type="line", x0=0, y0=0, x1=3000, y1=3000,
        line=dict(dash="dash", color="#414868"),
    )
    fig_scatter.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Fira Code, monospace", color="#a9b1d6", size=11),
        xaxis=dict(gridcolor="#292e42"), yaxis=dict(gridcolor="#292e42"),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.caption(
        "Points below the diagonal line show the WSCR penalty: "
        "CEP demand gets less capacity than conventional demand at the same node."
    )
