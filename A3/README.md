# A3 – Automated Verification of Structural Beam Claims  
### Advanced Building Design — DTU — 2025  
**Authors:** Aisha & Fashi  

---

# 1. About the Tool

## Problem / Claim

In the Advanced Building Design (ABD) course, structural teams frequently claim:

> “All primary reinforced concrete beams satisfy the minimum width requirement and Eurocode 2 minimum reinforcement rules.”

However:
- These checks are often done manually  
- They rely on spreadsheets or drawings  
- They are **not linked** to the IFC model  
- They are time-consuming and error-prone  

Our tool automates this process.

---

## Where the Problem Was Found

During the ABD course, we observed that several structural performance claims in the report were **not automatically verifiable** from the BIM model.

In particular:
- Minimum beam width (Eurocode 2)  
- Minimum longitudinal reinforcement  
- Minimum shear reinforcement  

These were documented manually instead of being evaluated directly from the IFC model.

---

## Description of the Tool

This tool is a Python script built using **IfcOpenShell** and **Pandas**, designed to:

### ✔ 1. Read all `IfcBeam` elements from an IFC model  
### ✔ 2. Extract beam cross-section dimensions from:
- `IfcMaterialProfileSetUsage`
- `IfcMaterialProfileSet`
- `IfcExtrudedAreaSolid.SweptArea`
- Beam names (e.g. “300x450”, “300x450 mm”)

### ✔ 3. Normalise the extracted geometry:
- Convert to millimetres  
- Identify  
  - `b_mm` = beam width  
  - `h_mm` = beam height  

### ✔ 4. Automatically evaluate Eurocode 2 minimum requirements:
- Minimum width (default: **200 mm**)  
- Minimum longitudinal reinforcement  
- Minimum shear resistance  
- Minimum stirrup reinforcement  

### ✔ 5. Compute key design values:
- `As_min_mm2`  
- `M_Rd_kNm`  
- `V_Rd_c_kN`  
- `V_Rd_s_kN`  

### ✔ 6. Export all values to an Excel file (`beam_results.xlsx`), including:
| Field | Description |
|-------|-------------|
| GlobalId | IFC beam ID |
| b_mm | beam width |
| h_mm | beam height |
| width_status | OK / NOT OK |
| As_min_mm2 | Minimum reinforcement |
| M_Rd_kNm | Bending resistance |
| V_Rd_c_kN | Shear resistance (concrete) |
| V_Rd_s_kN | Shear resistance (stirrups) |
| source | Profile / Name parsing / IFC Material section |

This provides **transparent** and **model-based evidence** for the structural claims in the ABD report.

---

# 2. Instructions to Run the Tool

## Requirements
- Python 3.x  
- Required packages:

```bash
`pip install ifcopenshell pandas openpyxl`

---

# 3.Running the program
