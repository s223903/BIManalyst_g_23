# A3 – Automated Verification of Structural Beam Claims  
### Advanced Building Design — DTU — 2025  
**Authors:** Aisha & Fashi  

---

# 1. About the Tool

## Problem / Claim
## Use Case Requirements

To fully support automated verification of structural beam requirements, the BIM model must contain:

1. **Beam Geometry**
   - Width and height (b × h) from:
     - IfcMaterialProfileSetUsage  
     - SweptArea → IfcExtrudedAreaSolid  
     - or Name-based dimensions (“300x450 mm”)

2. **Material Properties**
   - Concrete strength class (e.g., C30/37)
   - Steel reinforcement class (B500B)

3. **Location & Identification**
   - Every beam must have a unique `GlobalId`
   - Beam type and role (primary beam where applicable)

4. **Units & Model Context**
   - Model length unit (mm or m)
   - Consistent coordinate system

These requirements describe the minimum level of information the tool needs to verify EC2 beam dimensions and reinforcement assumptions.

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

###  1. Read all `IfcBeam` elements from an IFC model  
###  2. Extract beam cross-section dimensions from:
- `IfcMaterialProfileSetUsage`
- `IfcMaterialProfileSet`
- `IfcExtrudedAreaSolid.SweptArea`
- Beam names (e.g. “300x450”, “300x450 mm”)

###  3. Normalise the extracted geometry:
- Convert to millimetres  
- Identify  
  - `b_mm` = beam width  
  - `h_mm` = beam height  

###  4. Automatically evaluate Eurocode 2 minimum requirements:
- Minimum width (default: **200 mm**)  
- Minimum longitudinal reinforcement  
- Minimum shear resistance  
- Minimum stirrup reinforcement  

###  5. Compute key design values:
- `As_min_mm2`  
- `M_Rd_kNm`  
- `V_Rd_c_kN`  
- `V_Rd_s_kN`  

###  6. Export all values to an Excel file (`beam_results.xlsx`), including:
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

`pip install ifcopenshell pandas openpyxl`

---

## Running the program
###  1. Place your IFC file on your local machine.

###  2. Edit the path inside main.py:
`model_path = Path("C:/Users/.../YourModel.ifc")`

###  3. From the A3 folder, run:

`python main.py`

###  4.The tool generates:
`beam_results.xlsx`

in the folder

# 3. Process Diagrams
## Process Explanation

### As-Is Workflow (Manual)
The current ABD workflow relies on:
- Manually reading beam dimensions from drawings
- Entering values into spreadsheets
- Performing EC2 minimum checks by hand
- No connection between BIM model and documented claims

This process is time-consuming, error-prone and not traceable.
![As-Is](img/AS-IS.svg)


### To-Be Workflow (Automated with Our Tool)
The proposed workflow automates the entire verification process:

1. **Import IFC Model**  
   The script extracts all `IfcBeam` objects and identifies their cross-section.

2. **Extract Dimensions and Material Data**  
   The tool reads:
   - Profile dimensions  
   - SweptArea geometries  
   - Name-parsed dimensions when necessary  

3. **Run Eurocode Calculations**  
   The tool computes:
   - Minimum width check  
   - Minimum longitudinal reinforcement  
   - Minimum shear resistance  

4. **Generate Evidence File**  
   The script outputs an Excel file (`beam_results.xlsx`) containing:
   - Dimensions  
   - Status of EC2 width check  
   - Design resistances  
   - Data source (profile / type / name)

5. **Use in ABD Report**  
   The automatically generated results act as transparent, model-based evidence for structural safety claims.

This workflow eliminates manual checking and provides traceable, data-driven documentation.

![To-Be](img/TO-BE.png)
# 4. IDS – Information Delivery Specification

This IDS ensures that the IFC model contains the minimum information required for the tool.

`Requirements for Beam Width Automation:

Entities:
- Must contain IfcBeam elements  

Properties:
- Dimensions must be provided through at least ONE of the following:
  - IfcMaterialProfileSetUsage.Profile
  - IfcMaterialProfileSet.Profile
  - IfcExtrudedAreaSolid.SweptArea
  - Valid dimensional naming pattern (e.g. “300x450”)  

Units:
- Must contain IfcUnitAssignment with LENGTHUNIT (mm or m)

Material:
- Must contain concrete material (fck value defined externally in script)`


The corresponding IDS file is included as:

`A3/beam_width.ids`

# 5. Value of the Tool
## 5.1 Business Value

This tool provides significant value to engineering teams:

 Saves time

Manual Eurocode 2 checks on dozens of beams can take several hours.

 Reduces human error

Automated extraction avoids incorrect dimensions from outdated drawings.

 Improves traceability

Generates a full Excel report, where every number is backed by IFC data.

 Supports quality assurance

Model-based verification improves the ABD report and the final hand-in.

## 5.2 Societal Value
 Safer structures

Ensures reinforced concrete beams meet essential Eurocode 2 minimums.

- Supports digital construction workflows

Promotes transparent and reproducible engineering decisions.

- Encourages automation

A step toward fully automated code checking in BIM.

# 6. Files in This Repository
A3/
│── img/
│     ├── AS-IS.svg
│     ├── TO-BE.png
│
│── beam_check_tool.py
│── beam_width.ids
│── main.py
│── README.md   ← This file


# 7. Conclusion
## How the Tool Solves the Use Case

The developed tool directly addresses the identified ABD use case:

- It ensures that every primary reinforced concrete beam in the BIM model is checked  
  against Eurocode 2 minimum width and minimum reinforcement rules.
- It replaces manual spreadsheet-based verification with a fully automated workflow.
- It connects the structural model (IFC) to the performance claim in the ABD report.
- It generates transparent, repeatable and auditable evidence in Excel format.
- It enables consistency, traceability and correctness in BIM-based structural design.

This demonstrates a complete alignment between the BIM Use Case goal,
the tool’s functionality, the BPMN workflow, and the Information Exchange requirements.

