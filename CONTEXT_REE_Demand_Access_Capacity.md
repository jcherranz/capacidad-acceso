# CONTEXT: REE Demand Access Capacity File (Spain Transmission Grid)

This document provides complete context for working programmatically with the REE demand access capacity CSV file published on February 20, 2026. It covers the domain background, regulatory framework, data schema, data types, parsing quirks, enumerated values, key metrics, and known issues. It is intended to be self-contained so that a coding agent can process the file without external research.

---

## 1. WHAT THIS FILE IS

### 1.1 Origin

On February 20, 2026, Red Electrica de Espana (REE, part of Redeia group) published for the first time a file showing the available grid access capacity for new demand connections at every node (substation) of Spain's high-voltage transmission network (Red de Transporte, RdT). The file is published monthly as mandated by CNMC regulation.

Source URL: https://www.ree.es/es/clientes/consumidor/acceso-conexion/conoce-la-capacidad-de-acceso

### 1.2 What it answers

For any given node on Spain's transmission grid, the file answers: "How many MW of new demand (or storage) can be connected here, under what conditions, and if not, why not?"

### 1.3 Why it matters

Spain is experiencing an unprecedented surge in industrial electricity demand -- data centers for AI, electrolysers for green hydrogen, battery storage, and industrial electrification. Before this publication, promoters had to request capacity information node by node from REE and wait months for a response. This file is the first public, standardized, machine-readable map of where new demand can (and cannot) connect.

### 1.4 Regulatory background

- **CNMC Circular 1/2024**: Established the technical criteria for access capacity, including the WSCR criterion and the CEP/NO CEP classification.
- **CNMC EEDD December 2025**: "Especificaciones de Detalle" -- detailed technical specifications that oblige REE to publish demand access capacity monthly. REE attempted a 3-month delay citing unresolved agreements with distributors; CNMC rejected the postponement.
- **CNMC Resolution February 2026**: Announced pilot projects for dynamic voltage control and robustness regulation.

---

## 2. DOMAIN CONCEPTS

### 2.1 The Spanish electricity grid structure

Spain's grid has two layers:

- **Transmission network (Red de Transporte, RdT)**: High-voltage backbone at 400 kV, 220 kV, and in islands 132/66 kV. Managed by REE. Think of it as the motorway system.
- **Distribution network (Red de Distribucion, RdD)**: Medium/low voltage networks serving end consumers. Managed by several companies (i-DE/Iberdrola, e-distribucion/Endesa, UFD/Naturgy, Viesgo, etc.).

Nodes (nudos) are substations where these networks interconnect and where large consumers connect directly.

### 2.2 Access capacity

The access capacity of a node is the maximum power (MW) that can be newly connected at that point without compromising system security. It is calculated by applying five independent technical criteria simultaneously. The final available capacity is the **minimum** across all five -- a single saturated criterion closes the node.

### 2.3 CEP vs NO CEP (Power Electronics Classification)

**CEP (Consumo con Electronica de Potencia)**: Demand connected through power electronics (rectifiers, inverters, variable frequency drives). Examples:

- Data centers: UPS systems rectify AC to DC, store in batteries, invert back to AC. Server PSUs are rectifiers.
- Electrolysers: Rectify AC to DC for electrolysis.
- Modern industrial plants: Motor drives, arc furnaces with thyristor control.

**NO CEP**: Demand connected directly to the AC grid without power electronics intermediation. Examples: synchronous motors, resistive heaters, conventional transformers.

Why it matters: CEP loads do not provide mechanical inertia to the grid, can inject harmonics, and behave unpredictably during disturbances. High CEP penetration makes a node electrically "weaker." The WSCR criterion applies **only** to CEP loads.

In practice, any data center, electrolyser, or modern industrial facility will be classified as CEP. The CNMC threshold for CEP classification is defined in Circular 1/2024.

### 2.4 CH vs SH (Voltage Dip Ride-Through)

Within CEP demand, the file distinguishes:

- **CH (Con cumplimiento de Hueco de tension)**: Equipment designed to remain connected during voltage dips (sags), following a defined voltage-time curve. These devices can also contribute reactive current during disturbances, aiding grid recovery.
- **SH (Sin cumplimiento de Hueco de tension)**: Equipment that will disconnect during voltage dips.

**Critical fact**: The available capacity for SH equipment is **0 MW across the entire Spanish transmission network**. REE does not permit new CEP demand that cannot ride through voltage dips. This means voltage-dip ride-through compliance is a hard prerequisite for any new CEP connection -- it affects equipment procurement, UPS design, and electrical architecture from day one.

### 2.5 WSCR (Weighted Short-Circuit Ratio)

WSCR = effective short-circuit power at the node / total CEP power connected (weighted across interconnected nodes).

- **Short-circuit power** reflects how much synchronous generation (thermal, nuclear, hydro with alternators) is electrically close to the node. High short-circuit power = "strong" grid.
- As renewable generation (solar, wind via inverters) displaces synchronous generation, short-circuit power drops, making nodes weaker.
- A low WSCR means the grid cannot support more CEP demand without risking oscillations, protection malfunction, and power quality degradation.
- WSCR only constrains CEP demand; NO CEP demand is not affected by this criterion.

### 2.6 Reference value (Valor de referencia)

At every node where the transmission network connects to a distribution network, REE must reserve capacity for demand arriving through distribution (households, small businesses). The amount reserved is the "valor de referencia." Its determination requires a bilateral agreement between REE and the relevant distributor.

**Problem**: At the time of publication, only 235 out of 937 nodes have a resolved agreement (SI). 289 nodes have NO agreement, and 413 are marked N/A (no distribution connection or not applicable). For nodes where the agreement is unresolved (NO), REE cannot grant capacity to new direct-connected consumers because it does not know how much to reserve for distribution -- creating a regulatory bottleneck at 404 nodes (43%).

### 2.7 The five technical criteria

Each node is evaluated against all five criteria. The binding constraint (lowest value) determines the available capacity.

1. **WSCR (Criterio de Potencia de Cortocircuito)**: Is the short-circuit power sufficient for the amount of CEP load? Only applies to CEP demand. A node blocked by WSCR means there is not enough synchronous generation nearby to anchor the voltage for additional power-electronics demand. The grid is too electrically "weak" at that point.

2. **Static Demand (Criterio Estatico Demanda, Est_Dem)**: Can the physical network elements (lines, transformers, cables) carry the additional load under worst-case N-1 contingency without exceeding thermal limits? A node blocked by Est_Dem means cables, transformers, or lines are already at their thermal limit -- adding more MW would risk overheating.

3. **Static Storage (Criterio Estatico Almacenamiento, Est_Alm)**: Same thermal analysis but for storage assets in charging mode (batteries drawing power). Evaluated separately because storage has different consumption patterns (charge in off-peak, discharge in peak). A node blocked by Est_Alm means the same thermal constraint applies specifically to storage assets.

4. **Dynamic 1 -- Transient Stability (Criterio Dinamico 1, Din1)**: Can the system survive a sudden severe fault (e.g., three-phase short circuit cleared in ~150 ms) without generators losing synchronism? Tested via time-domain simulations. A node blocked by Din1 means that adding more load would risk a cascading trip after a sudden fault -- the system cannot recover fast enough. This is the **most frequent binding criterion** in the network (275 nodes).

5. **Dynamic 2 -- Dynamic Stability (Criterio Dinamico 2, Din2)**: Can the system damp inter-area power oscillations over seconds to minutes after a disturbance? A node blocked by Din2 means the grid would develop sustained oscillations after a disturbance, potentially spreading instability to neighbouring areas. Appears as secondary constraint at many nodes but is rarely the sole binding criterion.

### 2.8 Competitive tender (Concurso)

Some nodes have their remaining capacity allocated through a competitive tender process rather than first-come-first-served. Column 61 indicates "SI" for these nodes. There are 76 such nodes in the dataset.

---

## 3. FILE FORMAT AND PARSING

### 3.1 Basic format

- **Encoding**: UTF-8 with BOM (byte order mark at start)
- **Delimiter**: Semicolon (;)
- **Rows**: 941 total = 4 header rows + 937 data rows (one per node)
- **Columns**: 61 (numbered 1-61 in 1-based indexing)
- **Line endings**: Standard (CRLF or LF depending on download)

### 3.2 Header structure (CRITICAL for parsing)

The file has **4 merged header rows** that form a hierarchical column naming structure. This is the single most important parsing detail:

- **Row 1 (index 0)**: Top-level group names. Most cells are empty because the group name appears only in the first column of each group and spans multiple columns conceptually (but NOT via actual cell merging -- the intermediate cells are simply empty).
- **Row 2 (index 1)**: Sub-group names / individual column descriptions.
- **Row 3 (index 2)**: CEP / NO CEP / CEP (MPE) / NO CEP (MGES) classification for the margin, non-grantable, and available capacity blocks.
- **Row 4 (index 3)**: CH / SH sub-classification, and E / P (Existente / Prevista) for positions.

To get the full column name, you must concatenate information from all 4 rows. For example, column 56 (1-based):
- Row 1: "CAPACIDAD DE ACCESO DISPONIBLE PARA SOLICITUDES CRITERIO GENERAL"
- Row 2: "DEMANDA"
- Row 3: "CEP"
- Row 4: "CH"
- Full meaning: Available demand capacity for CEP demand with CH compliance.

### 3.3 Number formatting (CRITICAL)

Numeric values use **dot as thousands separator** and have **no decimal separator** (all values are integers). Examples:

- `1.310` means 1310 (one thousand three hundred and ten), NOT 1.31
- `250` means 250
- `0` means zero

**Parsing rule**: Strip dots from numeric fields before converting to integer. Do NOT interpret dots as decimal points.

Some numeric columns contain text values like `N/A`, empty strings, or whitespace-padded values (e.g., ` N/A `). These must be handled during parsing.

### 3.4 Special values across the file

| Value | Meaning | Where it appears |
|-------|---------|------------------|
| Empty string / whitespace | No data, not applicable, or no capacity | Many columns |
| `N/A` or ` N/A ` (with spaces) | Not applicable (e.g., no distribution connection, no shared zone) | Cols 11, 15, 19, 24 |
| `0` | Zero capacity or zero granted | Numeric columns |
| Checkmark `✓` | Physical bay exists or is planned | Cols 4-9 (positions) |
| `No` or `No ` (with trailing space) | No substation configuration limitation | Col 17 |
| `Si. Caso a)` / `Si. Caso b)` / `Si. Caso c)` | Yes, with specific case type | Col 17 |
| `SI` / `NO` | Agreement reached / not reached | Col 24 (estado acuerdo), Col 61 (concurso) |
| Text strings (criteria codes) | Binding criterion identifier | Cols 45-49 |
| Free text (motivo) | Reason capacity is non-grantable | Col 55 |

### 3.5 Positions columns (4-9): Special encoding

Columns 4-9 are three pairs of E (Existing) and P (Planned) for:
- Cols 4-5: Generation/Storage positions at the transmission network
- Cols 6-7: Demand (consumption) positions at the transmission network
- Cols 8-9: Distribution network connection positions

Values are either a checkmark (✓) or empty. These are not numeric. If a node has no demand position (cols 6-7 both empty), it cannot receive demand without prior civil works.

---

## 4. COMPLETE COLUMN SCHEMA (1-based indexing)

### Block A: Identification (cols 1-3)

| Col | CSV Header (Row 2) | Type | Description |
|-----|-------------------|------|-------------|
| 1 | Nombre y tension del nudo | String | Node name + voltage level in kV. Format: "NAME VOLTAGE". E.g., "ABADES 400", "ESCATRON 400". Same physical substation can appear multiple times at different voltages. |
| 2 | Codigo de subestacion | String (numeric code) | Unique substation identifier. Same code for different voltage levels of the same substation. |
| 3 | Comunidad Autonoma | String | Region (Autonomous Community). 18 unique values (see enumeration below). |

### Block B: Physical Positions (cols 4-9)

| Col | Sub-header | Type | Description |
|-----|-----------|------|-------------|
| 4 | Gen/Alm - E (Existente) | Checkmark/empty | Existing generation/storage bay |
| 5 | Gen/Alm - P (Prevista) | Checkmark/empty | Planned generation/storage bay |
| 6 | Consumo - E (Existente) | Checkmark/empty | Existing demand bay |
| 7 | Consumo - P (Prevista) | Checkmark/empty | Planned demand bay |
| 8 | Distribucion - E (Existente) | Checkmark/empty | Existing distribution connection |
| 9 | Distribucion - P (Prevista) | Checkmark/empty | Planned distribution connection |

### Block C: WSCR Criterion (cols 10-13)

| Col | Sub-header | Type | Description |
|-----|-----------|------|-------------|
| 10 | Capacidad de acceso nodal | Integer (dot-thousands) or empty | WSCR-based nodal access capacity (MW). Max CEP power the node can accept per short-circuit strength. |
| 11 | Binudos | String | Whether the node shares WSCR limit with another node. Usually "N/A" or a linked node name. |
| 12 | Afeccion de CS a seguridad del sistema | String | Security alerts. Values: empty, "Riesgo interacciones", "Superacion valor max Icc", "Superacion valor max Icc y riesgo interacciones". |
| 13 | Margen no ocupado | Integer or empty | WSCR margin not yet taken by granted permits (MW). |

### Block D: Static Demand Criterion (cols 14-17)

| Col | Sub-header | Type | Description |
|-----|-----------|------|-------------|
| 14 | Capacidad de acceso nodal | Integer (dot-thousands) or `N/A` | Thermal access capacity for demand (MW). TEXT-STORED in CSV -- requires numeric conversion. |
| 15 | Zona con capacidad compartida | String or `N/A` | Shared capacity zone code (SEPE code). Nodes in the same zone share a common thermal ceiling. |
| 16 | Margen no ocupado | Integer or empty | Static demand margin remaining (MW). |
| 17 | Limitaciones temporales de acceso | String | Substation configuration limitation. See enumerated values. |

### Block E: Static Storage Criterion (cols 18-20)

| Col | Sub-header | Type | Description |
|-----|-----------|------|-------------|
| 18 | Capacidad de acceso nodal | Integer (dot-thousands) or `N/A` | Thermal access capacity for storage in charging mode (MW). |
| 19 | Zona con capacidad compartida | String or `N/A` | Shared zone for storage. |
| 20 | Margen no ocupado | Integer or empty | Static storage margin remaining (MW). |

### Block F: Dynamic Criteria (cols 21-22)

| Col | Sub-header | Type | Description |
|-----|-----------|------|-------------|
| 21 | Margen no ocupado (Din1) | Integer or empty | Transient stability margin (MW). 0 = node saturated for transient stability. |
| 22 | Margen no ocupado (Din2) | Integer or empty | Dynamic stability margin (MW). 0 = node saturated for dynamic stability. |

### Block G: Granted Access Capacity Situation (cols 23-37)

| Col | Sub-header | Type | Description |
|-----|-----------|------|-------------|
| 23 | Valor de referencia (cap. acceso consumo RdD) | Integer or empty | MW reserved for distribution-connected demand. |
| 24 | Estado acuerdo valor de referencia | String | Agreement status: "SI", "NO", or "N/A". |
| 25 | Cap. otorgada demanda adicional al valor de referencia | Integer | Granted beyond reference value (MW). |
| 26 | Cap. otorgada demanda CEP con afeccion WSCR | Integer | Granted CEP demand affecting WSCR (MW). |
| 27 | Cap. otorgada demanda RdT | Integer | Total granted demand on transmission (MW). |
| 28 | Cap. demanda con aceptabilidad RdD | Integer | Demand with distribution-level acceptability (MW). |
| 29 | Cap. demanda RdD no incluida en valor de referencia | Integer | Distribution demand not in reference value (MW). |
| 30 | Cap. otorgada almacenamiento adicional al valor ref. | Integer | Granted storage beyond reference (MW). |
| 31 | Cap. otorgada almacenamiento RdT | Integer | Total granted storage on transmission (MW). |
| 32 | Cap. almacenamiento con aceptabilidad RdD | Integer | Storage with distribution acceptability (MW). |
| 33 | Cap. almacenamiento RdD no incluida en valor ref. | Integer | Distribution storage not in reference value (MW). |
| 34 | Cap. otorgada demanda CH RdT | Integer | Granted CH-compliant demand on transmission (MW). |
| 35 | Cap. otorgada demanda SH RdT | Integer | Granted SH demand on transmission (MW). |
| 36 | Cap. CH con aceptabilidad en RdD | Integer | CH with distribution acceptability (MW). |
| 37 | Cap. SH con aceptabilidad en RdD | Integer | SH with distribution acceptability (MW). |

### Block H: Pending Applications (cols 38-39)

| Col | Sub-header | Type | Description |
|-----|-----------|------|-------------|
| 38 | Cap. solicitada en curso demanda RdT | Integer | Demand applications pending resolution (MW). |
| 39 | Cap. solicitada en curso almacenamiento RdT | Integer | Storage applications pending resolution (MW). |

### Block I: Total Margin for RdT Connection (cols 40-44)

| Col | Sub-header (Row 3 + Row 4) | Type | Description |
|-----|---------------------------|------|-------------|
| 40 | DEMANDA - CEP - CH | Integer | Gross margin for CEP demand with CH compliance (MW). |
| 41 | DEMANDA - CEP - SH | Integer | Gross margin for CEP demand without CH (MW). Always 0. |
| 42 | DEMANDA - NO CEP | Integer | Gross margin for conventional demand (MW). |
| 43 | ALMACENAMIENTO - CEP (MPE) | Integer | Gross margin for CEP storage (MW). |
| 44 | ALMACENAMIENTO - NO CEP (MGES) | Integer | Gross margin for conventional storage (MW). |

### Block J: Binding Criteria (cols 45-49)

| Col | Sub-header | Type | Description |
|-----|-----------|------|-------------|
| 45 | DEMANDA - CEP - CH | String | Binding criterion for CEP CH demand. |
| 46 | DEMANDA - CEP - SH | String | Binding criterion for CEP SH demand. |
| 47 | DEMANDA - NO CEP | String | Binding criterion for conventional demand. |
| 48 | ALMACENAMIENTO - CEP (MPE) | String | Binding criterion for CEP storage. |
| 49 | ALMACENAMIENTO - NO CEP (MGES) | String | Binding criterion for conventional storage. |

### Block K: Non-Grantable Capacity (cols 50-55)

| Col | Sub-header | Type | Description |
|-----|-----------|------|-------------|
| 50 | DEMANDA - CEP - CH | Integer | MW technically available but non-grantable for regulatory reasons (CEP CH demand). |
| 51 | DEMANDA - CEP - SH | Integer | Same for CEP SH demand. |
| 52 | DEMANDA - NO CEP | Integer | Same for conventional demand. |
| 53 | ALMACENAMIENTO - CEP (MPE) | Integer | Same for CEP storage. |
| 54 | ALMACENAMIENTO - NO CEP (MGES) | Integer | Same for conventional storage. |
| 55 | Motivo capacidad no otorgable en RdT | String (free text) | Reason capacity is non-grantable. See enumerated values below. |

### Block L: Available Capacity for Applications (cols 56-60) -- THE KEY OUTPUT COLUMNS

| Col | Sub-header | Type | Description |
|-----|-----------|------|-------------|
| 56 | DEMANDA - CEP - CH | Integer or empty | **Available MW for new CEP demand (CH compliant)**. This is the primary column for data center / electrolyser projects. |
| 57 | DEMANDA - CEP - SH | Integer or empty | Available MW for CEP demand without CH. **Always 0 or empty across the entire network.** |
| 58 | DEMANDA - NO CEP | Integer or empty | Available MW for conventional (non-power-electronics) demand. |
| 59 | ALMACENAMIENTO - CEP (MPE) | Integer or empty | Available MW for CEP storage. |
| 60 | ALMACENAMIENTO - NO CEP (MGES) | Integer or empty | Available MW for conventional storage. |

### Block M: Competitive Tender (col 61)

| Col | Sub-header | Type | Description |
|-----|-----------|------|-------------|
| 61 | Nudo de concurso | String | "SI" if remaining capacity is allocated via competitive tender, empty otherwise. |

---

## 5. ENUMERATED VALUES

### 5.1 Comunidad Autonoma (col 3) -- 18 values

| Value | Node count |
|-------|-----------|
| Cataluna | 118 |
| Canarias | 99 |
| Andalucia | 94 |
| Comunidad de Madrid | 91 |
| Castilla y Leon | 86 |
| Islas Baleares | 78 |
| Comunidad Valenciana | 73 |
| Galicia | 60 |
| Aragon | 53 |
| Castilla-La Mancha | 48 |
| Pais Vasco | 38 |
| Extremadura | 34 |
| Region de Murcia | 17 |
| Principado de Asturias | 17 |
| Comunidad Foral de Navarra | 12 |
| Cantabria | 12 |
| La Rioja | 6 |
| Ceuta | 1 |

Note: The actual CSV values include accented characters (e.g., "Cataluna" is stored as "Cataluna" with tilde on the n, "Aragon" with accent on the o, etc.).

### 5.2 WSCR Alerts (col 12)

| Value | Count | Meaning |
|-------|-------|---------|
| (empty/whitespace) | 844 | No alert |
| "Riesgo interacciones" | 70 | Risk of harmonic/resonance interactions between power electronics |
| "Superacion valor max Icc" | 21 | Short-circuit current exceeds maximum allowed (equipment rating limit) |
| "Superacion valor max Icc y riesgo interacciones" | 2 | Both issues |

### 5.3 Substation Configuration Limitations (col 17)

| Value | Count | Meaning |
|-------|-------|---------|
| "No" or "No " | 745 | No limitation |
| "Si. Caso b)" | 158 | Temporary limitation, case b |
| "Si. Caso a)" | 18 | Temporary limitation, case a |
| "Si. Caso c)" | 16 | Temporary limitation, case c |

### 5.4 Reference Value Agreement Status (col 24)

| Value | Count | Meaning |
|-------|-------|---------|
| "N/A" | 413 | Not applicable (no distribution interface at this node) |
| "NO" | 289 | Agreement NOT reached between REE and distributor |
| "SI" | 235 | Agreement reached |

### 5.5 Binding Criteria Codes (cols 45-49)

These can appear individually or combined with "/" separator:

| Code | Count (col 45) | Meaning |
|------|----------------|---------|
| (empty) | 404 | No criterion reported (typically blocked for regulatory reasons before technical assessment) |
| Din1_Zona | 275 | Transient stability at zonal level |
| WSCR_Nudo | 118 | Short-circuit ratio at node level |
| Est_Dem_Nudo | 83 | Thermal overload at node level |
| Est_Dem_Zona | 33 | Thermal overload at zonal level |
| Est_Dem_Nudo/Din1_Zona | 10 | Combined thermal + transient |
| WSCR_Nudo/WSCR_Zona/Din1_Zona | 6 | Combined WSCR node + zone + transient |
| WSCR_Nudo/Din1_Zona | 5 | Combined WSCR + transient |
| WSCR_Zona | 1 | WSCR at zonal level only |
| Est_Dem_Nudo/Est_Dem_Zona/Din1_Zona | 1 | Triple combined |
| Est_Dem_Nudo/Est_Dem_Zona | 1 | Combined thermal node + zone |

**Parsing note**: Split on "/" to get individual criteria. The component codes are:

- `Din1_Zona`: Dynamic criterion 1 (transient stability), zonal
- `Din2_Zona`: Dynamic criterion 2 (dynamic stability), zonal
- `WSCR_Nudo`: WSCR at node level
- `WSCR_Zona`: WSCR at zonal level
- `Est_Dem_Nudo`: Static demand at node level
- `Est_Dem_Zona`: Static demand at zonal level
- `Est_Alm_Nudo`: Static storage at node level
- `Est_Alm_Zona`: Static storage at zonal level

### 5.6 Non-Grantable Reason (col 55)

| Value | Count | Meaning |
|-------|-------|---------|
| (empty) | 504 | No non-grantable capacity (either fully available or fully blocked technically) |
| "Valor de referencia no acordado. Valor de referencia no acordado en la zona estatica." | 186 | Reference value unresolved at both node and shared zone level |
| "Valor de referencia no acordado en la zona estatica." | 115 | Reference value unresolved at shared zone level only |
| "Valor de referencia no acordado." | 103 | Reference value unresolved at node level |
| "Nudo de concurso." | 23 | Capacity reserved for competitive tender |
| "Margen zonal reservado para concurso." | 6 | Zonal margin reserved for competitive tender |

**Parsing note**: These strings may have trailing spaces and/or periods. Normalize before comparison.

---

## 6. DATA QUALITY AND PARSING WARNINGS

### 6.1 Text-stored numbers

Columns 14 (Est_Dem nodal capacity), 16 (Est_Dem margin), 18 (Est_Alm nodal capacity), 20 (Est_Alm margin), and potentially others store numeric values as text strings in the CSV. When importing into tools like pandas or openpyxl:

- They may be read as strings, not numbers
- SUM, AVERAGE, and comparison operations will fail or produce wrong results
- **Fix**: After reading, strip whitespace, replace dots (thousands separator), handle "N/A" and empty strings, then convert to int/float

### 6.2 Dot-as-thousands separator

Applies to columns 10, 14, 18, and any numeric column with values >= 1000. The dot is NOT a decimal separator. Example: "1.310" = 1310 MW.

**Fix**: `value.replace('.', '')` before `int()` conversion (after handling N/A and empty).

### 6.3 Whitespace padding

Many values have leading/trailing spaces. Examples: ` N/A `, `No `, `  `. Always `.strip()` string values.

### 6.4 BOM character

The file starts with a UTF-8 BOM (byte order mark: EF BB BF). Use `encoding='utf-8-sig'` in Python or strip the BOM manually.

### 6.5 Empty vs zero vs N/A

These mean different things:

- **Empty string**: Field not applicable or no data reported. In available capacity columns (56-60), empty typically means capacity could not be determined (usually because of regulatory blockage).
- **0**: Explicitly zero -- the criterion was evaluated and the result is zero MW available.
- **N/A**: The criterion or classification does not apply to this node (e.g., WSCR binudos when there is no shared WSCR node, or shared zone when the node is not in a shared zone).

For aggregation: treat empty as 0 for summation, but track empty vs 0 separately for counting "blocked" vs "evaluated to zero."

### 6.6 Multi-header parsing strategy

Recommended approach in Python/pandas:

```python
import pandas as pd

# Read without headers, skip BOM
df = pd.read_csv('file.csv', sep=';', header=None, skiprows=4, encoding='utf-8-sig')

# Manually assign column names using the schema above
# Or read all 4 header rows to reconstruct names:
headers = pd.read_csv('file.csv', sep=';', header=None, nrows=4, encoding='utf-8-sig')
```

For the Excel file we created, the "Datos REE" tab has formatted headers in rows 1-4 with data starting at row 5, and columns are 1-indexed in Excel (A=1, B=2, ..., BI=61).

---

## 7. KEY AGGREGATE METRICS (from the February 2026 publication)

| Metric | Value |
|--------|-------|
| Total nodes | 937 |
| Nodes with 0 MW available (CEP CH) | ~705 (75%) |
| Nodes with >0 MW available (CEP CH) | ~232 (25%) |
| Total available CEP CH demand capacity | 39,643 MW |
| Total available CEP SH demand capacity | 0 MW (network-wide) |
| Total available NO CEP demand capacity | 63,732 MW |
| Nodes with unresolved reference value (col 24 = "NO") | 289 |
| Nodes with non-grantable capacity due to regulatory reasons | 404 (43%) |
| Nodes designated for competitive tender (col 61 = "SI") | 76 |
| Nodes with WSCR alerts (col 12 non-empty) | 93 |
| Nodes with substation config limitations (col 17 starts with "Si") | 192 |

### Regional breakdown (CEP CH available capacity, col 56)

| Region | Available MW (approx) |
|--------|----------------------|
| Galicia | 9,328 |
| Castilla y Leon | 7,902 |
| Andalucia | 7,488 |
| Castilla-La Mancha | 4,521 |
| Extremadura | 3,874 |
| Comunidad Valenciana | 2,318 |
| Region de Murcia | 1,753 |
| Principado de Asturias | 814 |
| Pais Vasco | 678 |
| Cantabria | 365 |
| Comunidad Foral de Navarra | 178 |
| La Rioja | 132 |
| Cataluna | 92 |
| Canarias | 88 |
| Aragon | 0 |
| Comunidad de Madrid | 0 |
| Islas Baleares | 0 |
| Ceuta | 0 |

### Binding criteria distribution (col 45, CEP CH demand)

| Criterion | Nodes blocked |
|-----------|--------------|
| Din1_Zona (transient stability) | 275 |
| WSCR_Nudo (short-circuit ratio) | 118 |
| Est_Dem_Nudo (thermal node) | 83 |
| Est_Dem_Zona (thermal zone) | 33 |
| Combined criteria | 24 |
| Empty (regulatory block before technical assessment) | 404 |

---

## 8. EXCEL FILE STRUCTURE

An Excel workbook (`Analisis_Capacidad_Demanda_RdT.xlsx`) was created with 7 tabs:

### Tab 1: "Datos REE"
Raw CSV import. 4 header rows + 937 data rows. Columns A-BI (61 columns). Frozen panes at D5. All numeric values converted from text to actual numbers.

### Tab 2: "Resumen por CCAA"
18 rows (one per region). Columns:
- CCAA name
- Node count (COUNTIF)
- Total available CEP CH (SUMIF on col BD/56)
- Total available NO CEP (SUMIF on col BF/58)
- Average WSCR capacity (AVERAGEIF)
- Nodes with 0 available (COUNTIFS)
- Nodes with unresolved agreement (COUNTIFS)

### Tab 3: "Indicadores Globales"
13 key metrics with formulas referencing "Datos REE". Includes derived ratios (% saturated, % unresolved, etc.).

### Tab 4: "Criterios Limitantes"
COUNTIF breakdown for each criterion code across columns AS-AW (45-49 in CSV).

### Tab 5: "Top Nudos Disponibles"
All 937 nodes with references to BD-BF (available capacity columns). Autofilter enabled for sorting/filtering.

### Tab 6: "Foco Madrid-Aragon-Cat"
Detailed COUNTIFS/SUMIFS for the three critical regions (Madrid, Aragon, Cataluna) where data center demand is concentrated but capacity is zero or near-zero.

### Tab 7: "Estado Acuerdos"
SI/NO/N/A breakdown per CCAA with percentage unresolved.

---

## 9. WORKED EXAMPLE: READING A NODE

### ESCATRON 400

| Column | Value | Interpretation |
|--------|-------|----------------|
| 1 (Name) | ESCATRON 400 | Substation Escatron, 400 kV |
| 3 (CCAA) | Aragon | In Aragon (0 MW available region) |
| 6 (Consumo E) | ✓ | Has existing demand bay -- physically can connect |
| 10 (WSCR cap) | ~402 | WSCR allows up to 402 MW CEP |
| 14 (Est_Dem cap) | value | Thermal criterion has some capacity |
| 21 (Din1 margin) | 0 | Transient stability margin exhausted |
| 22 (Din2 margin) | 0 | Dynamic stability margin also exhausted |
| 24 (Acuerdo) | SI | Reference value agreed |
| 27 (Otorgada dem RdT) | 402 | 402 MW already granted |
| 34 (Otorgada CH) | 402 | All granted demand is CH-compliant |
| 45 (Limitante) | Est_Dem_Nudo/Din1_Zona | Blocked by thermal AND transient stability |
| 55 (Motivo) | (empty) | No regulatory block -- purely technical |
| 56 (Disponible CEP CH) | 0 | Zero MW available |

Conclusion: Escatron 400 is technically saturated. The 402 MW that WSCR allows have already been granted. Even if WSCR had more room, Din1 (transient stability) is at 0 margin. No regulatory fix will help -- this node needs physical grid reinforcement or normative changes to dynamic stability criteria.

### ABANILLAS 400

| Column | Value | Interpretation |
|--------|-------|----------------|
| 1 (Name) | ABANILLAS 400 | Substation Abanillas, 400 kV |
| 3 (CCAA) | Region de Murcia | |
| 10 (WSCR cap) | 753 | WSCR allows 753 MW CEP |
| 21 (Din1 margin) | 847 | Transient stability margin = 847 MW |
| 22 (Din2 margin) | 0 | Dynamic stability exhausted |
| 45 (Limitante) | WSCR_Nudo | WSCR is the binding constraint |
| 56 (Disponible CEP CH) | 753 | 753 MW available for CEP CH |
| 58 (Disponible NO CEP) | 847 | 847 MW available for conventional |

Conclusion: This node has significant capacity. WSCR limits CEP to 753 MW, but conventional demand can go up to 847 MW. A data center here would be limited by WSCR; a conventional factory by Din1.

---

## 10. COMMON ANALYTICAL TASKS

For a coding agent working with this file, typical tasks include:

1. **Filter available nodes by region and capacity type**: Filter col 3 (CCAA) + check col 56/58/59/60 > 0.
2. **Identify why a node is blocked**: Check col 45-49 (criteria) + col 55 (motivo) + col 24 (acuerdo status).
3. **Aggregate capacity by region**: Group by col 3, sum cols 56-60.
4. **Find nodes with regulatory vs technical blocks**: Col 55 non-empty = regulatory block. Col 45 non-empty + col 56 = 0 = technical block. Col 45 empty + col 55 empty + col 56 empty = indeterminate.
5. **Assess WSCR risk**: Col 12 non-empty indicates security concerns even if capacity remains.
6. **Track concurso nodes**: Col 61 = "SI" -- capacity must go through tender, not first-come-first-served.
7. **Compare CEP vs NO CEP capacity**: Col 56 vs col 58 shows the WSCR penalty for power-electronics demand.
8. **Identify shared zones**: Col 15 (Est_Dem zones) and col 19 (Est_Alm zones) -- nodes in the same zone share a ceiling, so granting capacity at one reduces availability at others.

---

## 11. RELATIONSHIP BETWEEN COLUMNS (Logic Map)

```
Available capacity (cols 56-60) = Gross margin (cols 40-44) - Non-grantable (cols 50-54)

Gross margin (cols 40-44) = min(WSCR margin[col 13], Est_Dem margin[col 16], Est_Alm margin[col 20], Din1 margin[col 21], Din2 margin[col 22]) - Already granted (cols 25-37) - Pending (cols 38-39)

Non-grantable reasons (col 55):
  - "Valor de referencia no acordado" -> regulatory block (col 24 = "NO")
  - "Nudo de concurso" / "Margen zonal reservado para concurso" -> competitive tender (col 61 = "SI")

Binding criterion (cols 45-49) = whichever criterion produces the lowest margin
```

Note: This is a simplified logical model. The exact calculation by REE may involve more complex zone-level aggregation and weighted allocations. The column relationships above are the best reconstruction from the published data.

---

## 12. PYTHON PARSING TEMPLATE

```python
import pandas as pd

def load_ree_demand_capacity(filepath):
    """Load and parse the REE demand access capacity CSV file."""

    # Read data rows (skip 4 header rows), handle BOM
    df = pd.read_csv(
        filepath,
        sep=';',
        header=None,
        skiprows=4,
        encoding='utf-8-sig',
        dtype=str  # Read everything as string first
    )

    # Assign meaningful column names (0-indexed)
    col_names = [
        'nudo', 'cod_subestacion', 'ccaa',                          # 0-2
        'pos_gen_E', 'pos_gen_P', 'pos_con_E', 'pos_con_P',        # 3-6
        'pos_dist_E', 'pos_dist_P',                                  # 7-8
        'wscr_cap_nodal', 'wscr_binudos', 'wscr_alertas',          # 9-11
        'wscr_margen',                                               # 12
        'est_dem_cap_nodal', 'est_dem_zona', 'est_dem_margen',      # 13-15
        'est_dem_limit_temp',                                        # 16
        'est_alm_cap_nodal', 'est_alm_zona', 'est_alm_margen',    # 17-19
        'din1_margen', 'din2_margen',                                # 20-21
        'valor_referencia', 'estado_acuerdo',                        # 22-23
        'otorgada_dem_adicional', 'otorgada_dem_cep_wscr',          # 24-25
        'otorgada_dem_rdt', 'otorgada_dem_rdd',                     # 26-27
        'otorgada_dem_rdd_no_ref',                                   # 28
        'otorgada_alm_adicional', 'otorgada_alm_rdt',              # 29-30
        'otorgada_alm_rdd', 'otorgada_alm_rdd_no_ref',            # 31-32
        'otorgada_dem_ch_rdt', 'otorgada_dem_sh_rdt',              # 33-34
        'otorgada_ch_rdd', 'otorgada_sh_rdd',                      # 35-36
        'pendiente_dem_rdt', 'pendiente_alm_rdt',                   # 37-38
        'margen_dem_cep_ch', 'margen_dem_cep_sh',                   # 39-40
        'margen_dem_no_cep', 'margen_alm_cep', 'margen_alm_no_cep',# 41-43
        'limitante_dem_cep_ch', 'limitante_dem_cep_sh',             # 44-45
        'limitante_dem_no_cep', 'limitante_alm_cep',               # 46-47
        'limitante_alm_no_cep',                                      # 48
        'no_otorg_dem_cep_ch', 'no_otorg_dem_cep_sh',              # 49-50
        'no_otorg_dem_no_cep', 'no_otorg_alm_cep',                 # 51-52
        'no_otorg_alm_no_cep',                                      # 53
        'motivo_no_otorgable',                                       # 54
        'disp_dem_cep_ch', 'disp_dem_cep_sh',                      # 55-56
        'disp_dem_no_cep', 'disp_alm_cep', 'disp_alm_no_cep',    # 57-59
        'concurso'                                                   # 60
    ]
    df.columns = col_names[:len(df.columns)]

    # Clean and convert numeric columns
    numeric_cols = [
        'wscr_cap_nodal', 'wscr_margen',
        'est_dem_cap_nodal', 'est_dem_margen',
        'est_alm_cap_nodal', 'est_alm_margen',
        'din1_margen', 'din2_margen',
        'valor_referencia',
        'otorgada_dem_adicional', 'otorgada_dem_cep_wscr',
        'otorgada_dem_rdt', 'otorgada_dem_rdd',
        'otorgada_dem_rdd_no_ref',
        'otorgada_alm_adicional', 'otorgada_alm_rdt',
        'otorgada_alm_rdd', 'otorgada_alm_rdd_no_ref',
        'otorgada_dem_ch_rdt', 'otorgada_dem_sh_rdt',
        'otorgada_ch_rdd', 'otorgada_sh_rdd',
        'pendiente_dem_rdt', 'pendiente_alm_rdt',
        'margen_dem_cep_ch', 'margen_dem_cep_sh',
        'margen_dem_no_cep', 'margen_alm_cep', 'margen_alm_no_cep',
        'no_otorg_dem_cep_ch', 'no_otorg_dem_cep_sh',
        'no_otorg_dem_no_cep', 'no_otorg_alm_cep', 'no_otorg_alm_no_cep',
        'disp_dem_cep_ch', 'disp_dem_cep_sh',
        'disp_dem_no_cep', 'disp_alm_cep', 'disp_alm_no_cep',
    ]

    def parse_num(val):
        """Convert REE CSV numeric value to float."""
        if pd.isna(val):
            return 0.0
        val = str(val).strip()
        if val in ('', 'N/A'):
            return 0.0
        # Remove dots (thousands separator)
        val = val.replace('.', '')
        try:
            return float(val)
        except ValueError:
            return 0.0

    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_num)

    # Strip whitespace from string columns
    string_cols = ['nudo', 'ccaa', 'wscr_binudos', 'wscr_alertas',
                   'est_dem_zona', 'est_dem_limit_temp', 'est_alm_zona',
                   'estado_acuerdo', 'limitante_dem_cep_ch', 'limitante_dem_cep_sh',
                   'limitante_dem_no_cep', 'limitante_alm_cep', 'limitante_alm_no_cep',
                   'motivo_no_otorgable', 'concurso']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].fillna('').str.strip()

    return df
```

---

## 13. GLOSSARY

| Term | Spanish | Definition |
|------|---------|-----------|
| Access capacity | Capacidad de acceso | Max MW connectable at a node |
| Bay / position | Posicion / bahia | Physical connection point at a substation |
| Binding criterion | Criterio limitante | The criterion that sets the minimum (bottleneck) |
| CEP | Consumo con Electronica de Potencia | Power-electronics-interfaced demand |
| CH | Con cumplimiento de Hueco | Voltage-dip ride-through compliant |
| Competitive tender | Concurso | Allocation via bidding, not first-come-first-served |
| Distribution network | Red de Distribucion (RdD) | Medium/low voltage grid |
| Dynamic stability | Estabilidad dinamica (Din2) | Ability to damp oscillations post-disturbance |
| EEDD | Especificaciones de Detalle | Detailed technical specifications (CNMC) |
| Granted | Otorgada | Already allocated capacity |
| Margin | Margen | Remaining capacity before allocation |
| N-1 contingency | Contingencia N-1 | Loss of the single most critical element |
| NO CEP | Sin electronica de potencia | Conventional directly-connected demand |
| Node | Nudo | Substation / connection point |
| Non-grantable | No otorgable | Technically available but blocked by regulation |
| Pending | En curso / pendiente | Applications submitted but not yet resolved |
| Reference value | Valor de referencia | Capacity reserved for distribution demand |
| RdT | Red de Transporte | High-voltage transmission network |
| SH | Sin cumplimiento de Hueco | Not voltage-dip ride-through compliant |
| Short-circuit power | Potencia de cortocircuito | Measure of grid strength (synchronous contribution) |
| Transient stability | Estabilidad transitoria (Din1) | Ability to survive sudden faults |
| WSCR | Weighted Short-Circuit Ratio | Ratio of short-circuit power to CEP load |
