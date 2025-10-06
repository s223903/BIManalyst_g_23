# BIManalyst group 23
# A2 Submission

## A2a: About your group

Coding confidence (group score): 3 – Agree
Rationale: We can write and debug Python with ifcopenshell, including schema navigation, profile extraction, unit handling, and reporting.

Group focus area & roles:

Focus: Automated model checking for structural code compliance (beam width ≥ 200 mm).

Roles: 1 × Analyst (Python/IFC logic, testing)

## A2b: Identify Claim

Chosen building: Building #2516
Claim to check:

“All beams exposed to fire have a minimum width of 200 mm (Eurocode 2, Table 6.6).”

Short description:
We will read the IFC model, identify all IfcBeam elements, determine their cross-section dimensions (from profiles, body representations, or well-formed names/tags), compute width = min(b,h), and classify each beam as Correct (≥ 200 mm) or Incorrect (< 200 mm). Elements without readable dimensions are reported as Unknown.

Justification:
This check is simple, high-impact, and supports early design decisions and coordination. It creates measurable value (fast pass/fail, clear list of fixes) with minimal inputs.

## A2c: Use Case
<img width="1977" height="724" alt="image" src="https://github.com/user-attachments/assets/8c6ff11a-2499-4388-93cf-fc1c81be798e" />





## A2d: Scope the use case

Where a new script/tool is needed:

The dedicated step “Extract/parse section & check against 200 mm” is implemented by our Python tool BeamWidthChecker.

In the BPMN, highlight the single task node that ingests IFC, resolves section dimensions, and outputs pass/fail.

## A2e: Tool Idea
<img width="1562" height="735" alt="image" src="https://github.com/user-attachments/assets/ee98a031-da05-47ed-8ecc-adc42abca315" />



## A2f: Information Requirements

What we need from the model & where it is in IFC:

Beams: IfcBeam

Units: IfcUnitAssignment (LENGTHUNIT)

Profiles (preferred):

Material route: IfcRelAssociatesMaterial → IfcMaterialProfileSet(Usage) → MaterialProfiles[*].Profile

Body route: Representation('Body') → IfcExtrudedAreaSolid.SweptArea or IfcSectionedSolidHorizontal.CrossSections

IfcMappedItem → MappingSource.MappedRepresentation.Items (then same profile)

Typing: IfcRelDefinesByType → IfcBeamType (profile/name on type)

Fallback text: IfcBeam.Name, IfcBeam.Tag (regex “a×b” with optional units)

Is it in the model?

Usually yes for beams with standard profiles; if not, we rely on well-formed names/tags. Unstructured or BREP-only beams may appear as Unknown until authors add properties/names.

Do we know how to get it in ifcOpenShell?

Yes—by_type queries, traversal of relationships (HasAssociations, IsTypedBy), and reading Representation items.

What will we need to learn?

Making the regex tolerant to local naming conventions; handling edge cases (composite/arbitrary profiles) and documenting assumptions.

## A2g: Software licence
Using spyder and BPMM
