#!/usr/bin/env python3
"""Read-only research calculation; Python standard library, no application imports."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATEGORIES = ("direct", "partial", "reference_grounded")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(values, label):
    require(len(values) == len(set(values)), f"Duplicate {label}")
    return set(values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Also verify Markdown totals and local links")
    args = parser.parse_args()
    data = json.loads((ROOT / "coverage_mapping.json").read_text())
    concepts = data["concepts"]
    universe = unique([c["id"] for c in concepts], "concept IDs")
    unique([c["number"] for c in concepts], "concept numbers")
    require(all(c["kind"] in {"grade5_target", "prerequisite_bridge"} for c in concepts), "Unknown concept kind")
    grade5 = {c["id"] for c in concepts if c["kind"] == "grade5_target"}
    bridges = universe - grade5
    renderers = data["renderers"]
    registry = unique([r["id"] for r in renderers], "renderer IDs")
    core = {r["id"] for r in renderers if r["core"]}
    batch = unique(data["initial_batch"], "batch renderer IDs")
    require(batch <= core, "Batch contains unknown/non-Core renderer")
    excluded = {r["id"] for r in data["excluded_accepted"]}
    require("ten_frame_group_transfer" in excluded, "Make-Ten exclusion missing")
    require(not excluded & (universe | registry), "Excluded accepted activity entered planning universe")
    require({s["renderer"] for s in data["first_slices"]} == batch, "First-slice set differs from batch")
    unique([s["renderer"] for s in data["first_slices"]], "first slices")
    for item in renderers + data["first_slices"]:
        seen = set()
        for category in CATEGORIES:
            refs = unique(item[category], "mapping references")
            require(refs <= universe, "Unknown concept reference")
            require(not refs & seen, "Same renderer/concept assigned multiple categories")
            seen |= refs
        require(bool(item["rationale"]), "Missing coverage rationale")
    for item in data["first_slices"]:
        family = next(r for r in renderers if r["id"] == item["renderer"])
        require(set(item["direct"]) <= set(family["direct"]), "Slice direct support exceeds family")
        require(set().union(*(set(item[k]) for k in CATEGORIES)) <= set().union(*(set(family[k]) for k in CATEGORIES)), "Slice references exceed family")

    def classify(items, denominator):
        sets = {k: set().union(*(set(i[k]) for i in items)) & denominator for k in CATEGORIES}
        # One exclusive category per node; full support outranks other-family partial support.
        direct = sets["direct"]
        reference = sets["reference_grounded"] - direct
        partial = sets["partial"] - direct - reference
        uncovered = denominator - direct - reference - partial
        require(len(direct) + len(reference) + len(partial) + len(uncovered) == len(denominator), "Partition error")
        return {"direct": direct, "partial": partial, "reference_grounded": reference, "uncovered": uncovered}

    groups = {
        "Core families": [r for r in renderers if r["id"] in core],
        "Batch families": [r for r in renderers if r["id"] in batch],
        "First slices": data["first_slices"],
        "All planned families": renderers,
        "Implemented Grade 5": [],
    }
    lines = [f"Universe: {len(universe)} = {len(grade5)} Grade 5 targets + {len(bridges)} prerequisite bridges.",
             f"Families: {len(registry)} proposed; {len(core)} Core; {len(batch)} initial-batch families.",
             "", "| Scope | Denominator | Direct union | Direct % | Partial only | Reference-grounded only | Uncovered |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    partitions = {}
    for label, items in groups.items():
        for denominator_label, denominator in (("all nodes", universe), ("Grade 5 targets", grade5)):
            result = classify(items, denominator)
            partitions[label, denominator_label] = result
            d, p, r, u = (len(result[k]) for k in (*CATEGORIES, "uncovered"))
            lines.append(f"| {label} / {denominator_label} | {len(denominator)} | {d} | {100*d/len(denominator):.1f}% | {p} | {r} | {u} |")
    lines += ["", "| Renderer | Direct | Partial | Reference-grounded |", "|---|---:|---:|---:|"]
    for item in renderers:
        lines.append(f"| `{item['id']}` | {len(item['direct'])} | {len(item['partial'])} | {len(item['reference_grounded'])} |")
    legacy = data["legacy"]
    old_union = set().union(*(set(v) for v in legacy["catalog_core_associations"].values()))
    require(old_union <= universe - {"G5-NBT-DECIMAL-ADD-SUBTRACT"}, "Legacy contains new/unknown concept")
    lines += ["", f"Historical reported coverage: {legacy['reported_direct']}/{legacy['reported_concepts']} = {100*legacy['reported_direct']/legacy['reported_concepts']:.1f}%.",
              f"Historical catalog association union: {len(old_union)}/{legacy['reported_concepts']} = {100*len(old_union)/legacy['reported_concepts']:.1f}% (associations, not verified direct support)."]
    require(f"{100*legacy['reported_direct']/legacy['reported_concepts']:.1f}" == legacy["reported_percentage"], "Historical percentage mismatch")
    for label in groups:
        if label == "Implemented Grade 5":
            continue
        lines += ["", f"{label} — IDs (all nodes):"]
        for category, ids in partitions[label, "all nodes"].items():
            lines.append(f"- {category}: " + (", ".join(sorted(ids)) or "none"))
    report = "\n".join(lines)
    print(report)

    concept_md = (ROOT / "01_GRADE5_CONCEPT_MAP.md").read_text()
    md_pairs = re.findall(r"^\| (\d+) \| `([^`]+)`", concept_md, re.M)
    require([(int(n), key) for n, key in md_pairs] == [(c["number"], c["id"]) for c in concepts], "Concept Markdown/JSON mismatch")
    catalog = (ROOT / "03_RENDERER_CATALOG.md").read_text()
    catalog_keys = re.findall(r"^\| `([^`]+)` \|", catalog, re.M)
    require(unique(catalog_keys, "catalog renderer rows") == registry, "Catalog/JSON renderer mismatch")
    if args.check:
        coverage = (ROOT / "06_COVERAGE_AND_PRIORITY.md").read_text()
        block = coverage.split("<!-- CALCULATED:START -->\n", 1)[1].split("\n<!-- CALCULATED:END -->", 1)[0]
        require(block == report, "Displayed calculation block is stale")
        for path in ROOT.glob("*.md"):
            for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                if "://" not in link and not link.startswith("#"):
                    require((path.parent / link.split("#")[0]).exists(), f"Broken link in {path.name}: {link}")
        print("\nPASS: IDs, registry, reference resolution, unions, exclusions, subset rules, Markdown totals, local links.")


if __name__ == "__main__":
    main()
