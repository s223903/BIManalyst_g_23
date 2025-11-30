# main.py — Entry point for the A3 beam checking tool
# Authors: Aisha & Fashi — DTU ABD 2025

from pathlib import Path
import ifcopenshell
import pandas as pd

from beam_check_tool import (
    measure_profile_mm,
    bending_capacity_min_steel,
    shear_capacity_concrete,
    shear_capacity_min_stirrups,
    effective_depth,
    to_mm_scale
)



# -----------------------------------------
# USER SETTINGS
# -----------------------------------------

model_path = Path(r"C:\Users\Aisha Arfan\OneDrive - Danmarks Tekniske Universitet\Kandidat\1. Semester\BIM Modellering\A2 Use Case\25-16-D-STR.ifc")

MIN_WIDTH_MM = 200.0
OUTPUT_EXCEL = "beam_results.xlsx"

# -----------------------------------------

def main():

    if not model_path.is_file():
        raise FileNotFoundError(f"IFC file not found at: {model_path}")

    print("Opening IFC model...")
    ifc = ifcopenshell.open(str(model_path))

    mm_scale = to_mm_scale(ifc)
    beams = ifc.by_type("IfcBeam")

    print(f"Found {len(beams)} beams in the model.")

    results = []

    for b in beams:
        profile, source = measure_profile_mm(b, mm_scale)

        if profile is None:
            results.append({
                "GlobalId": b.GlobalId,
                "b_mm": None,
                "h_mm": None,
                "width_status": "UNKNOWN",
                "As_min_mm2": None,
                "M_Rd_kNm": None,
                "V_Rd_c_kN": None,
                "V_Rd_s_kN": None,
                "source": source[0]
            })
            continue

        b_mm, h_mm = profile
        width_status = "OK" if b_mm >= MIN_WIDTH_MM else "NOT OK"

        # EC2 calculations
        As_min, M_Rd_kNm = bending_capacity_min_steel(b_mm, h_mm)
        V_Rd_c_kN = shear_capacity_concrete(b_mm, h_mm)
        V_Rd_s_kN = shear_capacity_min_stirrups(b_mm, h_mm)

        results.append({
            "GlobalId": b.GlobalId,
            "b_mm": round(b_mm, 1),
            "h_mm": round(h_mm, 1),
            "width_status": width_status,
            "As_min_mm2": round(As_min, 2),
            "M_Rd_kNm": round(M_Rd_kNm, 2),
            "V_Rd_c_kN": round(V_Rd_c_kN, 2),
            "V_Rd_s_kN": round(V_Rd_s_kN, 2),
            "source": source[0]
        })

    # -----------------------------------------
    # EXPORT RESULTS TO EXCEL
    # -----------------------------------------

    df = pd.DataFrame(results)
    df.to_excel(OUTPUT_EXCEL, index=False)

    print("\n----------------------------------------")
    print("Beam Check Completed ✔")
    print(f"Results exported to: {OUTPUT_EXCEL}")
    print("----------------------------------------")


if __name__ == "__main__":
    main()

