"""Build terminology lookup entries (PubChem, RxNorm, MeSH) from the read-only KG.

One entry per
TerminologyConcept / ChemicalCompound node. Entries are never merged: a shared
name only adds the name to `ambiguous_names` of every entry that carries it.

Where names come from
- PubChem: Title (preferred); IUPACName and `synonym` properties in source order.
- RxNorm: name (preferred); `synonym` field and `RxNorm Synonym` properties.
  Codes (UNII, SNOMED CT, DrugBank) are not names and are not used.
- MeSH: rdfs:label, or prefLabel for Term subjects (which have no rdfs:label);
  aliases are the subject's own prefLabel, altLabel, entryVersion, casn1_label and
  the names of Term nodes reached by ONE explicit outgoing preferredTerm/term edge.
  No other MeSH relation (concept, narrowerConcept, mappedTo...) contributes names,
  so a descriptor does not inherit the synonyms of its concepts. A MeSH entry's
  `mesh_record_group` names the descriptor/SCR entries that own it instead.

`lookup_names` is the cleaned, folded subset of names meant for matching; `aliases`
and `normalized_names` keep everything for traceability.
"""

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

MESH_TERM_PREDICATES = ("preferredTerm", "term")  # also the alias order
MESH_NAME_PREDICATES = ("label", "prefLabel", "altLabel", "entryVersion", "casn1_label")
MESH_OWNER_PREDICATES = ("preferredConcept", "concept", "preferredTerm", "term")
MESH_RECORD_KINDS = ("TopicalDescriptor", "SCR_Chemical", "SCR_Organism")
ACCEPTED_LINK_TYPES = ("DENOTES_CONCEPT", "EXACT_MATERIAL_MATCH")
MAX_EXAMPLE_OCCURRENCES = 5
LOOKUP_NAME_CHARS = (3, 60)  # allowed folded length

# Wrong depositor synonyms found in review: PubChem CID -> folded names.
PUBCHEM_LOOKUP_DENY = {
    "2247": {"kelp"},
    "71263318": {"amino acids"},
    "161671": {"dong quai", "indian ginseng", "withania somnifera"},
    "24261": {"dietary fiber", "sand"},
    "15608515": {"dha"},
    "807": {"dry cough", "exceed", "i", "protect", "sweat"},
    "936": {"skin"},
    "702": {"advanced", "be safe", "care", "fast", "hand", "instant", "just 1", "lucky", "naturals", "not have", "professional", "regimen", "spectrum", "standard", "welcome"},
    "938": {"nah"},
    "586": {"iom"},
    "6137": {"met"},
    "18950": {"man"},
    "6274": {"his"},
    "10692": {"gluconates"},
    "2519": {"awake"},
    "3086051": {"protease", "proteolytic enzymes"},
    "753": {"moon"},
    "247": {"bet"},
    "10475633": {"glucoamylase"},
    "449171": {"vitamins"},
    "181572": {"psyllium"},
}

# Identifier-like alias heuristic, PubChem aliases only. It favours keeping real
# names: "vitamin B12", "MK-7", "CoQ10", IUPAC names and "[USP]"-tagged names are
# not flagged. Consumer product names and trade names ("Emersol 315") are names,
# not codes, so they are not flagged either. Any one pattern, the grade pattern or
# a molecular formula is enough.
IDENTIFIER_PATTERNS = [
    # InChIKey
    re.compile(r"[A-Z]{14}-[A-Z]{10}-[A-Z]"),
    # CAS / EC / EINECS numbers, optionally labelled; other purely numeric strings
    re.compile(r"(?:(?:CAS|EC|EINECS|ELINCS)[ :#-]*(?:no\.?|number)?[ :-]*)?\d[\d-]{2,}", re.I),
    # bare 10-character UNII: uppercase/digits with at least one of each
    re.compile(r"(?=.*\d)(?=.*[A-Z])[A-Z0-9]{10}"),
    # catalog code: one token with a run of 3+ digits (CHEMBL2106388, NSC-83511,
    # AB00373895_16, Prestwick0_000155). Punctuation used in chemical names
    # (commas, brackets, primes) is not allowed, nor a trailing word ("propane-123-triol").
    re.compile(r"(?=.*\d{3})(?!.*-[a-z]{4,}$)[A-Za-z0-9][A-Za-z0-9._:#/-]*"),
    # spaced registry code: known prefix followed by a number
    re.compile(
        r"(?:CCRIS|HSDB|NSC|UNII|BRN|AI3|FEMA|INS|UN|NCI|CHEBI|CHEMBL|SCHEMBL|RefChem|CID|SID"
        r"|DTXSID|DTXCID|DTXRID|Caswell|EPA Pesticide Chemical Code|Pesticide Code|C\.?I\.?|Colou?r Index"
        r"|Beilstein|Tox21|E|EU|ICSC|RTECS|MDL|MFCD|Epitope ID)"
        r"[ :#-]*(?:no\.?|number|-)?[ :#-]*[A-Za-z]{0,3}\d[\w./-]*",
        re.I,
    ),
    # ATC code (S01XA26)
    re.compile(r"[A-Z]\d{2}[A-Z]{2}\d{2}"),
]
# Grade / specification wording, searched anywhere in the alias.
GRADE_PATTERN = re.compile(
    r">=|≥|@ \d|\b(?:microg|mg)/d?L\b|\bmetals basis\b|\btrace metals\b|\bpuriss\b|\bpurum\b|\bpurity \d|\bACS reagent\b|\breagent grade\b"
    r"|\bculture grade\b|\bfirst grade\b|\bspecial grade\b|\b(?:food|feed)[ -]grade\b|\bLC/MS\b|\bfor ICP\b"
    r"|\b(?:analytical|reference|secondary|primary) standard\b|\breference material\b|\(Standard\)"
    r"|\bsuitable for\b|\bmeets\b.*\bspecifications\b|\bmesh\b|\bwire reel\b|\bfoil\b|\bthickness\b"
    r"|\bdiameter\b|\b\d+(?:\.\d+)?\s?(?:mm|mum|micron)\b|,.*\d\+?%|\b(?:BioXtra|BioReagent|ReagentPlus|BioUltra)\b",
    re.I,
)

# Product-like PubChem aliases (SPL product names deposited under ethanol, zinc
# oxide, nicotinamide, glycerol...). Keyword rule: only wording that marks a retail
# product. Bare brand names without such wording ("Sweet Pea") are not detected.
PRODUCT_PATTERN = re.compile(
    r"saniti[sz]|antisep|disinfect|\banti[- ]?(?:bac|microb|aging|wrinkle|itch)"
    r"|\bspf ?-?\d|\bfps \d|\bspf\b|sun ?screen|sun ?block|broad spectrum"
    r"|\bhands?[ -]?(?:gel|rub|wash|clean|wipe|hygiene|soap|foam)|\bwipes?\b|towelette|\bscent|unscented|fragrance"
    r"|moisturi[sz]|hydrating|\bskin ?care\b|\bface\b|\bfacial\b|\blip (?:balm|color|oil)|lipstick|lipshade"
    r"|\bmake-?up\b|\bfoundation\b|concealer|\bprimer\b|\btint(?:ed)?\b|\bcc cream"
    r"|\bcream\b(?! of tartar)|\blotion\b|\bserum\b(?! with reference)|\bbalm\b|\bointment\b|\bmask ?(?:pack)?\b|\btoner\b|\bampoule\b|\bessence\b"
    r"|shampoo|\bsoap\b|cleanser|cleansing|toothpaste|\bhair\b|\bmassage\b|\btrstay\b|whitening|brightening"
    r"|\bdiaper|\brash\b|antacid|laxative|suppositor|eye drops|\bnasal\b|\bteat\b|\bbaby\b|\bkids\b"
    r"|\b(?:extra|ultra|regular|maximum) strength\b|\bassorted\b|heartburn|\bflavor"
    r"|\d\s?(?:fl\.? ?)?oz\b|\b(?:walgreens|cvs|walmart|meijer|publix|kroger)\b",
    re.I,
)

# Molecular formula: element symbols with optional counts, brackets, dots and charges;
# needs a digit and two different elements, so "B12", "K2", "C60" stay names.
_ELEMENTS = (
    "He|Li|Be|Ne|Na|Mg|Al|Si|Cl|Ar|Ca|Sc|Ti|Cr|Mn|Fe|Co|Ni|Cu|Zn|Ga|Ge|As|Se|Br|Kr|Rb|Sr|Zr|Mo|Ag|Cd|Sn|Sb|Te"
    "|Xe|Cs|Ba|La|Ce|Pt|Au|Hg|Pb|Bi|H|B|C|N|O|F|P|S|K|V|I|W"
)
FORMULA_PATTERN = re.compile(rf"(?!SPF)(?=.*\d)(?:(?:{_ELEMENTS})\d*|[()\[\].·]\d*|[+-]\d*$|[+-](?=[A-Z(+-]))+")


def normalize_name(name: str) -> str:
    folded = unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", name).casefold())
    return " ".join(folded.split())


def fold_name(name: str) -> str:
    """Lookup folding: normalize_name, then every non-alphanumeric becomes a space."""
    return " ".join("".join(c if c.isalnum() else " " for c in normalize_name(name)).split())


def is_formula(alias: str) -> bool:
    return bool(FORMULA_PATTERN.fullmatch(alias)) and len(set(re.findall(_ELEMENTS, alias))) > 1


def is_identifier_like(alias: str) -> bool:
    alias = alias.strip()
    return (
        bool(GRADE_PATTERN.search(alias)) or is_formula(alias) or any(p.fullmatch(alias) for p in IDENTIFIER_PATTERNS)
    )


def _lookup_names(source: str, native_id: str, preferred, aliases, identifier_like) -> list[str]:
    excluded = set(identifier_like)
    names = [preferred] if preferred else []
    names += [a for a in aliases if a not in excluded and not (source == "pubchem" and PRODUCT_PATTERN.search(a))]
    denied = PUBCHEM_LOOKUP_DENY.get(native_id, set()) if source == "pubchem" else set()
    shortest, longest = LOOKUP_NAME_CHARS
    return sorted({n for n in map(fold_name, names) if shortest <= len(n) <= longest} - denied)


def _read_csv(path: Path):
    csv.field_size_limit(sys.maxsize)
    with open(path, encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def _local_name(uri: str) -> str:
    return re.split(r"[#/]", uri)[-1]


def _pointer_key(prop: dict) -> tuple:
    """Source order of a property; numeric pointer parts compare as numbers."""
    parts = prop["provenance"]["pointer"].split("/")
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in parts)


def _dedupe_aliases(names, preferred) -> list[str]:
    seen = {preferred.casefold()} if preferred else set()
    aliases = []
    for name in names:
        name = (name or "").strip()
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            aliases.append(name)
    return aliases


def _pubchem_names(props: dict):
    fields = props["original_fields"]
    synonyms = [p for p in props["source_properties"] if p["property_name"] == "synonym"]
    aliases = [fields.get("IUPACName")]
    aliases += [p["original_value"] for p in sorted(synonyms, key=_pointer_key)]
    return fields.get("Title"), aliases


def _rxnorm_names(props: dict):
    fields = props["original_fields"]
    synonyms = [p for p in props["source_properties"] if p["property_name"] == "RxNorm Synonym"]
    aliases = [fields.get("synonym")]
    aliases += [p["original_value"]["propValue"] for p in sorted(synonyms, key=_pointer_key)]
    return fields.get("name"), aliases


def _mesh_literals(props: dict, predicate: str) -> list[str]:
    """Literal values of one predicate: English/untagged first, then by value."""
    objects = [x["typed_object"] for x in props["rdf_literals"] if _local_name(x["predicate_uri"]) == predicate]
    objects.sort(key=lambda o: (o.get("xml:lang", "en") != "en", o.get("xml:lang", ""), o["value"]))
    return [o["value"] for o in objects]


def _mesh_own_names(props: dict) -> list[str]:
    """Preferred name first (rdfs:label, else prefLabel), then the subject's own aliases."""
    return [name for predicate in MESH_NAME_PREDICATES for name in _mesh_literals(props, predicate)]


def _entity_kind(source: str, props: dict) -> str:
    if source == "pubchem":
        return "compound"
    if source == "rxnorm":
        return props["original_fields"]["tty"]
    return "|".join(sorted(_local_name(t["value"]) for t in props["original_fields"]["types"]))


def _read_relationships(path: Path, nodes: dict):
    """Return MeSH term links {node: {(predicate rank, term node)}}, MeSH owners
    {node: nodes pointing to it by an owner predicate} and accepted occurrence links."""
    term_links, owners, accepted = defaultdict(set), defaultdict(set), defaultdict(set)
    for row in _read_csv(path):
        if row["type"] in ACCEPTED_LINK_TYPES:
            accepted[row["end_id"]].add((row["start_id"], row["type"]))
        elif row["type"] == "MESH_RELATION" and row["end_id"] in nodes:
            predicate = _local_name(json.loads(row["properties_json"])["predicate_uri"])
            if predicate in MESH_TERM_PREDICATES:
                term_links[row["start_id"]].add((MESH_TERM_PREDICATES.index(predicate), row["end_id"]))
            if predicate in MESH_OWNER_PREDICATES:
                owners[row["end_id"]].add(row["start_id"])
    unknown = sorted(set(accepted) - set(nodes))
    if unknown:
        raise ValueError(f"accepted links point to non-terminology nodes: {unknown[:5]}")
    return term_links, owners, accepted


def _mesh_record_group(node_id: str, owners: dict, kinds: dict) -> list[str]:
    """Descriptor/SCR entries owning this node: Term -> Concept -> descriptor, upward only."""
    if kinds[node_id] in MESH_RECORD_KINDS:
        return [node_id]
    return sorted({record for owner in owners[node_id] for record in _mesh_record_group(owner, owners, kinds)})


def build_terminology(graph_dir: Path, tokenizer) -> list[dict]:
    """Return one lookup entry per terminology node, sorted by kg_node_id.

    `tokenizer` is a tokenizers.Tokenizer (truncation/padding disabled) or None.
    """
    if tokenizer is not None and (tokenizer.truncation or tokenizer.padding):
        raise ValueError("tokenizer must have truncation and padding disabled")
    graph_dir = Path(graph_dir)
    nodes = {}
    for filename in ("TerminologyConcept.csv", "ChemicalCompound.csv"):
        for row in _read_csv(graph_dir / "nodes" / filename):
            if row["id"] in nodes:
                raise ValueError(f"duplicate node id {row['id']}")
            nodes[row["id"]] = (row, json.loads(row["properties_json"]))
    term_links, owners, accepted = _read_relationships(graph_dir / "relationships" / "relationships.csv", nodes)
    kinds = {node_id: _entity_kind(props["source"], props) for node_id, (_, props) in nodes.items()}

    entries = []
    for node_id in sorted(nodes):
        row, props = nodes[node_id]
        source = props["source"]
        description, flags = None, []
        if source == "pubchem":
            preferred, names = _pubchem_names(props)
        elif source == "rxnorm":
            preferred, names = _rxnorm_names(props)
        elif source == "mesh":
            names = _mesh_own_names(props)
            preferred = names[0] if names else None
            for _, term_id in sorted(term_links[node_id]):
                names += _mesh_own_names(nodes[term_id][1])
            description = next(iter(_mesh_literals(props, "scopeNote")), None)
            if "false" in _mesh_literals(props, "active"):
                flags.append("inactive_in_source")
        else:
            raise ValueError(f"unexpected source {source!r} for {node_id}")

        preferred = (preferred or "").strip() or None
        aliases = _dedupe_aliases(names, preferred)
        if preferred is None:
            flags.append("no_preferred_name")
        if source == "pubchem" and preferred and is_identifier_like(preferred):
            flags.append("identifier_like_preferred_name")
        # the record's own formula counts even when it is a single element ("I2")
        own_formula = str(props["original_fields"].get("MolecularFormula") or "").casefold()
        own_formula = own_formula if any(c.isdigit() for c in own_formula) else ""
        identifier_like = [
            a for a in aliases
            if source == "pubchem" and (is_identifier_like(a) or (own_formula and a.casefold() == own_formula))
        ]
        links = accepted[node_id]
        occurrence_ids = sorted({occurrence for occurrence, _ in links})
        entries.append({
            "entry_id": node_id,
            "source": source,
            "kg_node_id": node_id,
            "kg_node_type": row["type"],
            "native_id": props["native_id"],
            "preferred_name": preferred,
            "aliases": aliases,
            "identifier_like_aliases": identifier_like,
            "normalized_names": sorted({normalize_name(n) for n in [preferred or "", *aliases]} - {""}),
            "ambiguous_names": [],  # filled below, once all entries exist
            "lookup_names": _lookup_names(source, props["native_id"], preferred, aliases, identifier_like),
            "ambiguous_lookup_names": [],  # filled below
            "mesh_record_group": _mesh_record_group(node_id, owners, kinds) if source == "mesh" else None,
            "description": description,
            "description_token_count": len(tokenizer.encode(description).ids) if tokenizer and description else None,
            "entity_kind": kinds[node_id],
            "accepted_occurrence_links": {
                "count": len(links),
                "example_occurrence_ids": occurrence_ids[:MAX_EXAMPLE_OCCURRENCES],
                "relation_types": sorted({relation for _, relation in links}),
            },
            "mapping_approval": props["mapping_approval"],
            "evidence_ids": json.loads(row["evidence_ids"]),
            "match_policy": "propose_candidates_only",
            "flags": sorted(flags),
        })

    for names_key, ambiguous_key in (("normalized_names", "ambiguous_names"), ("lookup_names", "ambiguous_lookup_names")):
        counts = Counter(name for entry in entries for name in entry[names_key])
        for entry in entries:
            entry[ambiguous_key] = [n for n in entry[names_key] if counts[n] > 1]
    return entries


def _print_summary(entries: list[dict]) -> None:
    print(f"entries: {len(entries)}")
    for (source, kind), count in sorted(Counter((e["source"], e["entity_kind"]) for e in entries).items()):
        print(f"  {source:8} {kind:18} {count}")
    print("flags:", dict(sorted(Counter(f for e in entries for f in e["flags"]).items())))
    sources_by_name = defaultdict(set)
    for entry in entries:
        for name in entry["ambiguous_names"]:
            sources_by_name[name].add(entry["source"])
    cross = sum(len(s) > 1 for s in sources_by_name.values())
    print(f"ambiguous names: {len(sources_by_name)} distinct, {cross} across sources, "
          f"{sum(bool(e['ambiguous_names']) for e in entries)} entries affected")
    print(f"aliases: {sum(len(e['aliases']) for e in entries)}, "
          f"identifier-like: {sum(len(e['identifier_like_aliases']) for e in entries)}")
    for source in ("mesh", "pubchem", "rxnorm"):
        group = [e for e in entries if e["source"] == source]
        print(f"lookup names {source}: {sum(len(e['lookup_names']) for e in group)} of "
              f"{sum(len(e['normalized_names']) for e in group)} normalized, "
              f"{sum(not e['lookup_names'] for e in group)} entries empty")
    print("ambiguous lookup names:", len({n for e in entries for n in e["ambiguous_lookup_names"]}))
    print("descriptions:", sum(e["description"] is not None for e in entries),
          "max tokens:", max((e["description_token_count"] or 0 for e in entries), default=0) or None)
    for source in ("mesh", "pubchem", "rxnorm"):
        for entry in [e for e in entries if e["source"] == source and e["accepted_occurrence_links"]["count"]][:2]:
            sample = {k: v[:6] if isinstance(v, list) else v for k, v in entry.items()}
            print(json.dumps(sample, ensure_ascii=False, sort_keys=True, indent=1))


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Summarize terminology lookup entries (read-only).")
    parser.add_argument("--graph-dir", type=Path, default=root / "data/graph/full-graph-concepts-v1-08c99550a0fa0f86aca9")
    parser.add_argument("--tokenizer", type=Path, default=root / ".cache/medcpt_tokenizer/tokenizer.json")
    parser.add_argument("--out", type=Path, help="optional JSONL output")
    args = parser.parse_args()

    tokenizer = None
    if args.tokenizer.exists():
        from tokenizers import Tokenizer
        tokenizer = Tokenizer.from_file(str(args.tokenizer))
        tokenizer.no_truncation()
        tokenizer.no_padding()
    entries = build_terminology(args.graph_dir, tokenizer)
    _print_summary(entries)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            for entry in entries:
                handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
