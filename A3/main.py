
"""
Beam check based on Eurocode 2:
- Reads beam cross-sections from an IFC model
- Checks minimum width
- Estimates bending and shear capacity
- Exports results to Excel (if pandas is available) or CSV as fallback
"""

from pathlib import Path
import re
import ifcopenshell
import math
import argparse
import csv  


IFC_PATH = r"IFC FILE HERE"
MIN_WIDTH_MM = 200.0       

# --- Material and design parameters (EC2) ---
FCK = 30.0                 # concrete strength (MPa), e.g. C30/37
FYK = 500.0                # steel yield strength (MPa), e.g. B500
GAMMA_C = 1.5
GAMMA_S = 1.15

# --- Detailing assumptions ---
C_NOM = 30.0               
BAR_DIAM = 16.0            
STIRRUP_DIAM = 8.0         
LEGS_STIRRUP = 2           
S_STIRRUPS = None          
THETA_DEG = 45.0           
Z_OVER_D = 0.9             
RHO_L_MAX = 0.02           

# ========================

# -------- units --------
def to_mm_scale(ifc):
    """Return scale factor to convert model length to mm."""
    try:
        ua = ifc.by_type("IfcUnitAssignment")[0]
        for u in ua.Units:
            if u.is_a("IfcSIUnit") and u.UnitType == "LENGTHUNIT":
                return 1000.0 * (0.001 if getattr(u, "Prefix", None) == "MILLI" else 1.0)
    except Exception:
        pass
    return 1000.0

# -------- profile helpers (no geometry engine) --------
def dims_from_profile(p):
    """Return (dx, dy) in model units from common IfcProfileDef types."""
    if not p:
        return None
    t = p.__class__.__name__

    if t == "IfcRectangleProfileDef":
        return float(p.XDim), float(p.YDim)
    if t == "IfcIShapeProfileDef":
        return float(p.OverallWidth), float(p.OverallDepth)
    if t in ("IfcTShapeProfileDef", "IfcUShapeProfileDef"):
        return float(p.FlangeWidth), float(p.Depth)
    if t == "IfcLShapeProfileDef":
        return float(p.Width), float(p.Depth)
    if t == "IfcCircleProfileDef":
        d = 2 * float(p.Radius)
        return d, d
    if t == "IfcEllipseProfileDef":
        return 2 * float(p.SemiAxis1), 2 * float(p.SemiAxis2)

    # Arbitrary → bounding box
    if t in ("IfcArbitraryClosedProfileDef", "IfcArbitraryProfileDefWithVoids"):
        oc = p.OuterCurve
        if oc and oc.is_a("IfcPolyline"):
            xs, ys = zip(*[(pt.Coordinates[0], pt.Coordinates[1]) for pt in oc.Points])
            return (max(xs) - min(xs), max(ys) - min(ys))
        if oc and oc.is_a("IfcIndexedPolyCurve") and oc.Points and oc.Points.is_a("IfcCartesianPointList2D"):
            xs, ys = zip(*oc.Points.CoordList)
            return (max(xs) - min(xs), max(ys) - min(ys))

    # Composite → first profile
    if t == "IfcCompositeProfileDef" and getattr(p, "Profiles", None):
        return dims_from_profile(p.Profiles[0])

    return None

def get_profile_from_material(prod):
    """Try to get profile from material profile set."""
    for rel in getattr(prod, "HasAssociations", []) or []:
        if rel.is_a("IfcRelAssociatesMaterial"):
            m = rel.RelatingMaterial
            if m and m.is_a("IfcMaterialProfileSetUsage") and m.ForProfileSet:
                for mp in (m.ForProfileSet.MaterialProfiles or []):
                    if getattr(mp, "Profile", None):
                        return mp.Profile
            if m and m.is_a("IfcMaterialProfileSet"):
                for mp in (m.MaterialProfiles or []):
                    if getattr(mp, "Profile", None):
                        return mp.Profile
    return None

def get_profile_from_representation(prod):
    """Try to get profile from Body representation."""
    rep = getattr(prod, "Representation", None)
    if not rep:
        return None

    for r in rep.Representations or []:
        if r.RepresentationIdentifier != "Body":
            continue
        for it in r.Items or []:
            if it.is_a("IfcExtrudedAreaSolid") and getattr(it, "SweptArea", None):
                return it.SweptArea
            if it.is_a("IfcSectionedSolidHorizontal") and getattr(it, "CrossSections", None):
                if it.CrossSections:
                    return it.CrossSections[0]
            if it.is_a("IfcMappedItem") and it.MappingSource and it.MappingSource.MappedRepresentation:
                for sub in it.MappingSource.MappedRepresentation.Items or []:
                    if sub.is_a("IfcExtrudedAreaSolid") and getattr(sub, "SweptArea", None):
                        return sub.SweptArea
    return None

def get_type(prod):
    for rel in getattr(prod, "IsTypedBy", []) or []:
        if rel.is_a("IfcRelDefinesByType") and rel.RelatingType:
            return rel.RelatingType
    return None

# -------- name parsing --------
NUMXNUM = re.compile(
    r"(?P<a>\d+(?:\.\d+)?)\s*[x×]\s*(?P<b>\d+(?:\.\d+)?)(?:\s*(?P<u>mm|millimeter[s]?|cm|m))?",
    re.IGNORECASE
)

def dims_from_text(name_or_tag, mm_scale):
    if not name_or_tag:
        return None

    m = NUMXNUM.search(str(name_or_tag))
    if not m:
        return None

    a, b = float(m.group("a")), float(m.group("b"))
    unit = (m.group("u") or "").lower()

    if unit == "mm" or "millimeter" in unit:
        ax = a; bx = b
    elif unit == "cm":
        ax = a * 10.0; bx = b * 10.0
    elif unit == "m":
        ax = a * 1000.0; bx = b * 1000.0
    else:
        if max(a, b) > 10.0:
            ax = a; bx = b
        else:
            ax = a * 1000.0; bx = b * 1000.0

    return ax / mm_scale, bx / mm_scale

# -------- profile extraction --------
def measure_profile_mm(beam, mm_scale):
    p = get_profile_from_material(beam) or get_profile_from_representation(beam)
    dims = dims_from_profile(p)
    if dims:
        dx_mm, dy_mm = dims[0]*mm_scale, dims[1]*mm_scale
        return tuple(sorted((dx_mm, dy_mm))), ("profile", (dx_mm, dy_mm))

    t = get_type(beam)
    if t:
        p = get_profile_from_representation(t) or get_profile_from_material(t)
        dims = dims_from_profile(p)
        if dims:
            dx_mm, dy_mm = dims[0]*mm_scale, dims[1]*mm_scale
            return tuple(sorted((dx_mm, dy_mm))), ("type_profile", (dx_mm, dy_mm))

    for text in (
        getattr(beam, "Name", None),
        getattr(beam, "Tag", None),
        getattr(t, "Name", None) if t else None,
        getattr(t, "Tag", None) if t else None,
    ):
        dims = dims_from_text(text, mm_scale)
        if dims:
            dx_mm, dy_mm = dims[0]*mm_scale, dims[1]*mm_scale
            return tuple(sorted((dx_mm, dy_mm))), ("name_parse", (dx_mm, dy_mm, str(text)))

    return None, ("unknown", None)

# ---- EC2 formulas ----
def f_ctm_from_fck(fck=FCK):
    return 0.3 * (fck ** (2.0 / 3.0))

def rho_l_min(fck=FCK, fyk=FYK):
    fctm = f_ctm_from_fck(fck)
    return max(0.26 * fctm / fyk, 0.0013)

def lever_arm(d):
    return Z_OVER_D * d

def effective_depth(h_mm):
    return max(h_mm - C_NOM - STIRRUP_DIAM - 0.5 * BAR_DIAM, 0.0)

def bending_capacity_min_steel(b_mm, h_mm):
    d = effective_depth(h_mm)
    if d <= 0 or b_mm <= 0:
        return 0.0, 0.0
    rho_min = rho_l_min(FCK, FYK)
    As_min = rho_min * b_mm * d
    z = lever_arm(d)
    M_Rd_kNm = (As_min * (FYK / GAMMA_S) * z) / 1e6
    return As_min, M_Rd_kNm

def shear_capacity_concrete(b_mm, h_mm):
    d = effective_depth(h_mm)
    if d <= 0 or b_mm <= 0:
        return 0.0
    rho = min(rho_l_min(FCK, FYK), RHO_L_MAX)
    k = min(1.0 + math.sqrt(200.0 / d), 2.0)
    term = (100.0 * rho * FCK) ** (1.0 / 3.0)
    V_Rd_c_kN = (0.18 / GAMMA_C) * k * term * b_mm * d / 1000.0
    return V_Rd_c_kN

def shear_capacity_min_stirrups(b_mm, h_mm):
    d = effective_depth(h_mm)
    if d <= 0 or b_mm <= 0:
        return 0.0
    z = lever_arm(d)
    Asw_s_min = 0.08 * math.sqrt(FCK) / FYK * b_mm * LEGS_STIRRUP
    cot_theta = 1.0 / math.tan(math.radians(THETA_DEG))
    V_Rd_s_kN = (Asw_s_min * z * (FYK / GAMMA_S) * cot_theta) / 1000.0
    return V_Rd_s_kN

# -------- main --------
def run(path, min_width_mm=200.0, print_each=True):
    p = Path(path)
    if not p.exists():
        print(f"File not found: {p}")
        return

    ifc = ifcopenshell.open(str(p))
    mm = to_mm_scale(ifc)
    beams = list(ifc.by_type("IfcBeam"))

    ok = not_ok = unknown = 0
    results = []

    for b in beams:
        profile, source = measure_profile_mm(b, mm)
        if profile is None:
            unknown += 1
            if print_each:
                print(f"- {b.GlobalId}: no usable cross-section found")
            continue

        b_mm, h_mm = profile
        width_status = "OK" if b_mm >= min_width_mm else "NOT OK"
        if width_status == "OK":
            ok += 1
        else:
            not_ok += 1

        As_min, M_Rd = bending_capacity_min_steel(b_mm, h_mm)
        V_Rd_c = shear_capacity_concrete(b_mm, h_mm)
        V_Rd_s = shear_capacity_min_stirrups(b_mm, h_mm)

        if print_each:
            print(
                f"- {b.GlobalId}: b={b_mm:.0f} mm, h={h_mm:.0f} mm "
                f"→ width check: {width_status}"
            )
            print(
                f"    As,min ≈ {As_min:.0f} mm², M_Rd ≈ {M_Rd:.1f} kNm"
            )
            print(
                f"    Shear: V_Rd,c ≈ {V_Rd_c:.1f} kN, "
                f"V_Rd,s ≈ {V_Rd_s:.1f} kN"
            )

        results.append({
            "GlobalId": b.GlobalId,
            "b_mm": b_mm,
            "h_mm": h_mm,
            "width_status": width_status,
            "As_min_mm2": As_min,
            "M_Rd_kNm": M_Rd,
            "V_Rd_c_kN": V_Rd_c,
            "V_Rd_s_kN": V_Rd_s,
            "source": source[0],
        })

    total = ok + not_ok + unknown
    print("\n--- Beam check summary ---")
    print(f"Total beams: {total}")
    print(f"Width OK (≥ {min_width_mm:.0f} mm): {ok}")
    print(f"Width NOT OK (< {min_width_mm:.0f} mm): {not_ok}")
    print(f"Unknown dimensions: {unknown}")

    # ---- Excel / CSV export ----
    # Først prøver vi Excel (kræver pandas + openpyxl/xlsxwriter)
    try:
        import pandas as pd
        out_xlsx = p.with_suffix(".beam_check.xlsx")
        df = pd.DataFrame(results)
        df.to_excel(out_xlsx, index=False)
        print(f"\nExcel-fil gemt → {out_xlsx}")
    except ImportError:
        # fallback: CSV hvis pandas ikke findes
        out_csv = p.with_suffix(".beam_check.csv")
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "GlobalId","b_mm","h_mm","width_status",
                    "As_min_mm2","M_Rd_kNm","V_Rd_c_kN","V_Rd_s_kN","source"
                ]
            )
            writer.writeheader()
            writer.writerows(results)
        print("\n(pandas ikke installeret – gemmer som CSV i stedet)")
        print(f"CSV-fil gemt → {out_csv}")

# -------- CLI entry point --------
def main():
    parser = argparse.ArgumentParser(description="Beam check based on Eurocode 2.")
    parser.add_argument("--ifc", type=str, default=IFC_PATH, help="Path to IFC file")
    parser.add_argument("--min-width", type=float, default=MIN_WIDTH_MM, help="Minimum beam width in mm")
    parser.add_argument("--summary-only", action="store_true", help="Only print summary (no per-beam details)")
    args = parser.parse_args()

    run(args.ifc, min_width_mm=args.min_width, print_each=not args.summary_only)

if __name__ == "__main__":
    main()
