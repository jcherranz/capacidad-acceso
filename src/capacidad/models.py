"""Column definitions, constants, and enums for REE demand access capacity data."""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DEFAULT_CSV = DATA_RAW / "2026_02_20_GRT_demanda.csv"
DEFAULT_ZIP_URL = (
    "https://d1n1o4zeyfu21r.cloudfront.net/CapacidadDeAcceso/"
    "2026_02_20_GRT_demanda.zip"
)

# 61 column names (0-indexed, matching 1-based cols 1-61 from CONTEXT)
COLUMN_NAMES = [
    "nudo",                     # 0  - Node name + voltage
    "cod_subestacion",          # 1  - Substation code
    "ccaa",                     # 2  - Autonomous community
    "pos_gen_E",                # 3  - Existing generation/storage bay
    "pos_gen_P",                # 4  - Planned generation/storage bay
    "pos_con_E",                # 5  - Existing demand bay
    "pos_con_P",                # 6  - Planned demand bay
    "pos_dist_E",               # 7  - Existing distribution connection
    "pos_dist_P",               # 8  - Planned distribution connection
    "wscr_cap_nodal",           # 9  - WSCR nodal capacity (MW)
    "wscr_binudos",             # 10 - Shared WSCR node
    "wscr_alertas",             # 11 - WSCR security alerts
    "wscr_margen",              # 12 - WSCR margin (MW)
    "est_dem_cap_nodal",        # 13 - Static demand nodal capacity (MW)
    "est_dem_zona",             # 14 - Shared capacity zone
    "est_dem_margen",           # 15 - Static demand margin (MW)
    "est_dem_limit_temp",       # 16 - Substation config limitations
    "est_alm_cap_nodal",        # 17 - Static storage nodal capacity (MW)
    "est_alm_zona",             # 18 - Shared storage zone
    "est_alm_margen",           # 19 - Static storage margin (MW)
    "din1_margen",              # 20 - Dynamic 1 margin (MW)
    "din2_margen",              # 21 - Dynamic 2 margin (MW)
    "valor_referencia",         # 22 - Reference value (MW)
    "estado_acuerdo",           # 23 - Agreement status
    "otorgada_dem_adicional",   # 24 - Granted demand beyond reference
    "otorgada_dem_cep_wscr",    # 25 - Granted CEP demand affecting WSCR
    "otorgada_dem_rdt",         # 26 - Total granted demand RdT
    "otorgada_dem_rdd",         # 27 - Demand with distribution acceptability
    "otorgada_dem_rdd_no_ref",  # 28 - Distribution demand not in ref value
    "otorgada_alm_adicional",   # 29 - Granted storage beyond reference
    "otorgada_alm_rdt",         # 30 - Total granted storage RdT
    "otorgada_alm_rdd",         # 31 - Storage with distribution acceptability
    "otorgada_alm_rdd_no_ref",  # 32 - Distribution storage not in ref value
    "otorgada_dem_ch_rdt",      # 33 - Granted CH demand RdT
    "otorgada_dem_sh_rdt",      # 34 - Granted SH demand RdT
    "otorgada_ch_rdd",          # 35 - CH with distribution acceptability
    "otorgada_sh_rdd",          # 36 - SH with distribution acceptability
    "pendiente_dem_rdt",        # 37 - Pending demand applications
    "pendiente_alm_rdt",        # 38 - Pending storage applications
    "margen_dem_cep_ch",        # 39 - Gross margin CEP CH demand
    "margen_dem_cep_sh",        # 40 - Gross margin CEP SH demand
    "margen_dem_no_cep",        # 41 - Gross margin NO CEP demand
    "margen_alm_cep",           # 42 - Gross margin CEP storage
    "margen_alm_no_cep",        # 43 - Gross margin NO CEP storage
    "limitante_dem_cep_ch",     # 44 - Binding criterion CEP CH
    "limitante_dem_cep_sh",     # 45 - Binding criterion CEP SH
    "limitante_dem_no_cep",     # 46 - Binding criterion NO CEP
    "limitante_alm_cep",        # 47 - Binding criterion CEP storage
    "limitante_alm_no_cep",     # 48 - Binding criterion NO CEP storage
    "no_otorg_dem_cep_ch",      # 49 - Non-grantable CEP CH
    "no_otorg_dem_cep_sh",      # 50 - Non-grantable CEP SH
    "no_otorg_dem_no_cep",      # 51 - Non-grantable NO CEP
    "no_otorg_alm_cep",         # 52 - Non-grantable CEP storage
    "no_otorg_alm_no_cep",      # 53 - Non-grantable NO CEP storage
    "motivo_no_otorgable",      # 54 - Reason non-grantable
    "disp_dem_cep_ch",          # 55 - Available CEP CH demand (MW) **KEY**
    "disp_dem_cep_sh",          # 56 - Available CEP SH demand (MW)
    "disp_dem_no_cep",          # 57 - Available NO CEP demand (MW)
    "disp_alm_cep",             # 58 - Available CEP storage (MW)
    "disp_alm_no_cep",          # 59 - Available NO CEP storage (MW)
    "concurso",                 # 60 - Competitive tender flag
]

# Column classification
NUMERIC_COLUMNS = [
    "wscr_cap_nodal", "wscr_margen",
    "est_dem_cap_nodal", "est_dem_margen",
    "est_alm_cap_nodal", "est_alm_margen",
    "din1_margen", "din2_margen",
    "valor_referencia",
    "otorgada_dem_adicional", "otorgada_dem_cep_wscr",
    "otorgada_dem_rdt", "otorgada_dem_rdd",
    "otorgada_dem_rdd_no_ref",
    "otorgada_alm_adicional", "otorgada_alm_rdt",
    "otorgada_alm_rdd", "otorgada_alm_rdd_no_ref",
    "otorgada_dem_ch_rdt", "otorgada_dem_sh_rdt",
    "otorgada_ch_rdd", "otorgada_sh_rdd",
    "pendiente_dem_rdt", "pendiente_alm_rdt",
    "margen_dem_cep_ch", "margen_dem_cep_sh",
    "margen_dem_no_cep", "margen_alm_cep", "margen_alm_no_cep",
    "no_otorg_dem_cep_ch", "no_otorg_dem_cep_sh",
    "no_otorg_dem_no_cep", "no_otorg_alm_cep", "no_otorg_alm_no_cep",
    "disp_dem_cep_ch", "disp_dem_cep_sh",
    "disp_dem_no_cep", "disp_alm_cep", "disp_alm_no_cep",
]

STRING_COLUMNS = [
    "nudo", "cod_subestacion", "ccaa",
    "wscr_binudos", "wscr_alertas",
    "est_dem_zona", "est_dem_limit_temp", "est_alm_zona",
    "estado_acuerdo",
    "limitante_dem_cep_ch", "limitante_dem_cep_sh",
    "limitante_dem_no_cep", "limitante_alm_cep", "limitante_alm_no_cep",
    "motivo_no_otorgable", "concurso",
]

POSITION_COLUMNS = [
    "pos_gen_E", "pos_gen_P",
    "pos_con_E", "pos_con_P",
    "pos_dist_E", "pos_dist_P",
]

# Key output columns (available capacity for applications)
AVAILABLE_CAPACITY_COLUMNS = [
    "disp_dem_cep_ch",   # CEP demand with CH compliance
    "disp_dem_cep_sh",   # CEP demand without CH (always 0)
    "disp_dem_no_cep",   # Conventional demand
    "disp_alm_cep",      # CEP storage
    "disp_alm_no_cep",   # Conventional storage
]

MARGIN_COLUMNS = [
    "margen_dem_cep_ch", "margen_dem_cep_sh",
    "margen_dem_no_cep", "margen_alm_cep", "margen_alm_no_cep",
]

BINDING_CRITERIA_COLUMNS = [
    "limitante_dem_cep_ch", "limitante_dem_cep_sh",
    "limitante_dem_no_cep", "limitante_alm_cep", "limitante_alm_no_cep",
]

# Domain constants
EXPECTED_ROWS = 937
EXPECTED_COLS = 61

CCAA_LIST = [
    "Andalucía", "Aragón", "Canarias", "Cantabria",
    "Castilla y León", "Castilla-La Mancha", "Cataluña",
    "Ceuta", "Comunidad de Madrid", "Comunidad Foral de Navarra",
    "Comunidad Valenciana", "Extremadura", "Galicia",
    "Islas Baleares", "La Rioja", "País Vasco",
    "Principado de Asturias", "Región de Murcia",
]

AGREEMENT_VALUES = {"SI", "NO", "N/A"}

CRITERIA_CODES = {
    "Din1_Zona", "Din2_Zona",
    "WSCR_Nudo", "WSCR_Zona",
    "Est_Dem_Nudo", "Est_Dem_Zona",
    "Est_Alm_Nudo", "Est_Alm_Zona",
}

CAPACITY_LABELS = {
    "disp_dem_cep_ch": "CEP CH Demand",
    "disp_dem_cep_sh": "CEP SH Demand",
    "disp_dem_no_cep": "NO CEP Demand",
    "disp_alm_cep": "CEP Storage",
    "disp_alm_no_cep": "NO CEP Storage",
}
