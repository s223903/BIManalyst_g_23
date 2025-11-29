# A3 – Automated Verification of Structural Beam Claims  
### Advanced Building Design — DTU — 2025  
**Author:** Aisha and Fashi 

---

## 1. About the Tool

### Problem / Claim

In Advanced Building Design reports, structural teams frequently claim:

> “All primary reinforced concrete beams satisfy the minimum width requirement and Eurocode 2 minimum reinforcement rules.”

Today, this is almost always checked manually, using drawings and spreadsheets.  
This is time-consuming and error-prone, and there is no automatic link between the IFC model and the design claim.

### Where we found the problem

During the ABD course we observed that several structural safety claims in the design reports were not automatically verifiable from the BIM model.  
The minimum width requirement for reinforced concrete beams is one of the most common undocumented assumptions.

### Description of the tool

The tool is a Python script using **IfcOpenShell** that:

1. Reads all `IfcBeam` elements from an IFC model.  
2. Extracts cross-section dimensions (b × h) from:
   - `IfcMaterialProfileSetUsage` (material profile sets)  
   - the Body representation (`IfcExtrudedAreaSolid.SweptArea`)  
   - or, as a fallback, parses beam names/tags like `"300x450"` or `"300x450 mm"`.
3. Converts dimensions to millimetres and identifies:
   - `b_mm` = beam width (smaller side)  
   - `h_mm` = beam height (larger side)
4. Checks a **minimum width requirement** (default: 200 mm).  
5. Estimates **Eurocode 2 design capacities** based on minimum reinforcement:
   - minimum longitudinal reinforcement area `As_min`  
   - bending resistance `M_Rd`  
   - concrete shear resistance `V_Rd,c`  
   - shear resistance from minimum stirrups `V_Rd,s`.
6. Exports all results to an **Excel file (.xlsx)**, one row per beam, with:
   - `GlobalId`  
   - `b_mm`, `h_mm`  
   - `width_status` (OK / NOT OK)  
   - `As_min_mm2`, `M_Rd_kNm`, `V_Rd_c_kN`, `V_Rd_s_kN`  
   - `source` (profile / type_profile / name_parse)

This provides transparent, model-based evidence for the claims in the ABD report.

### Instructions to run the tool

#### Requirements

- Python 3.x  
- Packages:

```bash
pip install ifcopenshell pandas openpyxl

