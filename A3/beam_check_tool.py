
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
import csv  # used as fallback if pandas is not available

# --- Global settings ---
FCK = 30.0            
FYK = 500.0           
GAMMA_C = 1.5
GAMMA_S = 1.15

C_NOM = 30.0          
BAR_DIAM = 16.0       
STIRRUP_DIAM = 8.0    
LEGS_STIRRUP = 2      
S_STIRRUPS = None     
THETA_DEG = 45.0      
Z_OVER_D = 0.9        
RHO_L_MAX = 0.02      


def to_mm_scale(ifc):
    try:
        ua = ifc.by_type("IfcUnitAssignment")[0]
        for u in ua.Units:
            if u.is_a("IfcSIUnit") and u.UnitType == "LENGTHUNIT":
                return 1000.0 * (0.001 if getattr(u, "Prefix", None) == "MILLI" else 1.0)
    except Exception:
        pass
    return 1000.0


def dims_from_profile(p):
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

    if t in ("IfcArbitraryClosedProfileDef", "IfcArbitraryProfileDefWithVoids"):
        oc = p.OuterCurve
        if oc and oc.is_a("IfcPolyline"):
            xs, ys = zip(*[(pt.Coordinates[0], pt.Coordinates[1]) for pt in oc.Points])
            return (max(xs) - min(xs), max(ys) - min(ys))
        if oc and oc.is_a("IfcIndexedPolyCurve") and oc.Points and oc.Points.is_a("IfcCartesianPointList2D"):
            xs, ys = zip(*oc.Points.CoordList)
            return (max(xs) - min(xs), max(ys) - min(ys))

    if t == "IfcCompositeProfileDef" and getattr(p, "Profiles", None):
        return dims_from_profile(p.Profiles[0])

    return None


def get_profile_from_material(prod):
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
    rep = getattr(prod, "Representation", None)
    if not rep:
        return None

    for r in rep.Representations or []:
        if r.RepresentationIdentifier != "Body":
            continue
        for it in r.Items or []:
            if it.is_a("IfcExtrudedAreaSolid") and getattr(it, "SweptArea", None):
                return it.SweptArea
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


# --- regex fallback for dimensions ---
NUMXNUM = re.compile(
    r"(?P<a>\d+(?:\.\d+)?)\s*[x×]\s*(?P<b>\d+(?:\.\d+)?)(?:\s*(?P<u>mm|millimeter[s]?|cm|m))?",
    re.IGNORECASE,
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
        ax, bx = a, b
    elif unit == "cm":
        ax, bx = a * 10.0, b * 10.0
    elif unit == "m":
        ax, bx = a * 1000.0, b * 1000.0
    else:
        if max(a, b) > 10.0:
            ax, bx = a, b
        else:
            ax, bx = a * 1000.0, b * 1000.0

    return ax / mm_scale, bx / mm_scale


def measure_profile_mm(beam, mm_scale):
    p = get_profile_from_material(beam) or get_profile_from_representation(beam)
    dims = dims_from_profile(p)
    if dims:
        dx_mm, dy_mm = dims[0] * mm_scale, dims[1] * mm_scale
        return tuple(sorted((dx_mm, dy_mm))), ("profile", (dx_mm, dy_mm))

    t = get_type(beam)
    if t:
        p = get_profile_from_representation(t) or get_profile_from_material(t)
        dims = dims_from_profile(p)
        if dims:
            dx_mm, dy_mm = dims[0] * mm_scale, dims[1] * mm_scale
            return tuple(sorted((dx_mm, dy_mm))), ("type_profile", (dx_mm, dy_mm))

    for text in (
        getattr(beam, "Name", None),
        getattr(beam, "Tag", None),
        getattr(t, "Name", None) if t else None,
        getattr(t, "Tag", None) if t else None,
    ):
        dims = dims_from_text(text, mm_scale)
        if dims:
            dx_mm, dy_mm = dims[0] * mm_scale, dims[1] * mm_scale
            b_mm, h_mm = sorted((dx_mm, dy_mm))
            return (b_mm, h_mm), ("name_parse", (dx_mm, dy_mm, str(text)))

    return None, ("unknown", None)


# --- EC2 calculations ---
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
    M_Rd_Nmm = As_min * (FYK / GAMMA_S) * z
    return As_min, M_Rd_Nmm / 1e6  


def shear_capacity_concrete(b_mm, h_mm):
    d = effective_depth(h_mm)
    if d <= 0 or b_mm <= 0:
        return 0.0

    rho = min(rho_l_min(FCK, FYK), RHO_L_MAX)
    k = min(1.0 + math.sqrt(max(200.0 / d, 0.0)), 2.0)
    term = (100.0 * rho * FCK) ** (1.0 / 3.0)
    V_Rd_c_N = (0.18 / GAMMA_C) * k * term * b_mm * d
    return V_Rd_c_N / 1000.0


def shear_capacity_min_stirrups(b_mm, h_mm):
    d = effective_depth(h_mm)
    if d <= 0 or b_mm <= 0:
        return 0.0

    z = lever_arm(d)
    Asw_per_s_min = 0.08 * math.sqrt(FCK) / FYK * b_mm
    Asw_per_s_min *= LEGS_STIRRUP

    cot_theta = 1.0 / math.tan(math.radians(THETA_DEG))
    V_Rd_s_N = Asw_per_s_min * z * (FYK / GAMMA_S) * cot_theta
    return V_Rd_s_N / 1000.0


# --- MAIN ---
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
                print(f"- {b.GlobalId}: no cross-section found")
            continue

        b_mm, h_mm = profile
        status = "OK" if b_mm >= min_width_mm else "NOT OK"
        if status == "OK":
            ok += 1
        else:
            not_ok += 1

        As_min, M_Rd = bending_capacity_min_steel(b_mm, h_mm)
        V_Rd_c = shear_capacity_concrete(b_mm, h_mm)
        V_Rd_s = shear_capacity_min_stirrups(b_mm, h_mm)

        if print_each:
            print(f"- {b.GlobalId}: b={b_mm:.0f} mm, h={h_mm:.0f} mm → {status}")

        results.append({
            "GlobalId": b.GlobalId,
            "b_mm": round(b_mm),
            "h_mm": round(h_mm),
            "width_status": status,
            "As_min_mm2": round(As_min, 1),
            "M_Rd_kNm": round(M_Rd, 2),
            "V_Rd_c_kN": round(V_Rd_c, 2),
            "V_Rd_s_kN": round(V_Rd_s, 2),
            "source": source[0],
        })

    print("\n--- Beam width check summary ---")
    print(f"Total beams: {ok+not_ok+unknown}")
    print(f"OK beams: {ok}")
    print(f"NOT OK: {not_ok}")
    print(f"Unknown: {unknown}")

    try:
        import pandas as pd
        out_xlsx = p.with_suffix(".beam_check.xlsx")
        pd.DataFrame(results).to_excel(out_xlsx, index=False)
        print(f"Saved Excel → {out_xlsx}")
    except ImportError:
        out_csv = p.with_suffix(".beam_check.csv")
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "GlobalId", "b_mm", "h_mm", "width_status",
                    "As_min_mm2", "M_Rd_kNm", "V_Rd_c_kN", "V_Rd_s_kN", "source"
                ],
            )
            writer.writeheader()
            writer.writerows(results)
        print(f"Saved CSV → {out_csv}")

