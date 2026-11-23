"""Prepare BM25 / MedCPT indexing inputs from the frozen KG export (read-only).

Builds no index and no embedding, and never edits the KG.
Run:      supplementsrx_env/bin/python scripts/prepare_indexing_inputs.py
"""
import argparse
import csv
import hashlib
import json
import re
import shutil
import statistics
import tempfile
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import tokenizers
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
GRAPH = "data/graph/full-graph-concepts-v1-08c99550a0fa0f86aca9"
NATMED_RAW = "data/raw/natmedpro/records.jsonl"

# Everything here feeds the corpus version hash and is copied into the manifest.
CONFIG = {
    "schema": "indexing-inputs-v1",
    "tokenizer": {
        "model": "ncbi/MedCPT-Article-Encoder",
        "revision": "d05a736da4bb84ee4057b7f7999485be6ed85465",
        "library": "tokenizers==0.22.2",
        "files": {
            "tokenizer.json": "6e046044df8a2fcedb10607075dca187cae61d806c0d80a96c5b81017edc90c9",
            "tokenizer_config.json": "cabeefb4bbba68c42d40a56bfc1e73dd2e5dfb6e0ca90a66349519c375452d1e",
            "config.json": "3fea00b31d018d676d6b7e2f6cddcfe1abc69bcb88f5f09f51b848212e1671d1",
        },
        "encoding": "encode(context, text) with special tokens; truncation and padding disabled",
    },
    "max_tokens": 512,
    # Measured on the context alone, without special tokens.
    "max_context_tokens": 128,
    "short_text_words": 20,
    "very_short_text_words": 5,
    "short_comment_words": 20,
    "parent_snippet_words": 40,
    "bm25_text": "bm25_context + '\\n' + index_text",
    "medcpt_pair": "(context, index_text)",
    "context_templates": {
        "natmed": "{title} | {section}[ | {heading active at start} (continued); {heading}; ...]",
        "dsld": "{fullName}[ ({brandName})] | {type}",
        "reddit_post": "Reddit post | {title}",
        "reddit_comment": "Reddit comment | Thread: {thread post title}[ | Replying to: {parent snippet}]",
        "reddit_comment_no_thread": "Reddit comment | r/{subreddit}[ | Replying to: {parent snippet}]",
        "bm25_context": "context without the parent snippet",
    },
    # Verbatim claim field used as heading, by claim_type (dose has none). In
    # "interactions with conditions" a null interaction.partner falls back to population.
    "natmed_heading_fields": {
        "effectiveness": "indication", "interaction": "interaction.partner",
        "adverse_effect": "adverse_effect_category", "safety": "population",
    },
    "natmed_rating_fields": {
        "effectiveness": "effectiveness_rating", "interaction": "interaction.rating",
        "safety": "safety_rating",
    },
    # Sections without claims: see raw_line_headings() for the full rule.
    "natmed_raw_line_headings": {
        "section": "nutrient depletions", "marker_line": "Depletion Rating",
        "rating_lines": ["MAJOR", "MODERATE", "INSIGNIFICANT"], "max_heading_chars": 60,
    },
    "splitting": "only over max_tokens; greedy; sentence/newline, then whitespace, then character boundary; "
                 "context, links and citations follow each part's own span",
    "terminal_word_regex": r"[.!?][\)\]\"”’]*$",
    "username_regex": r"\bu/\w+",
    # Reddit usernames. Case-sensitive and at least 3 characters, so the lab unit "U/L" is left alone. Reddit
    # markdown may escape underscores ("overview\\_for\\_name"). Group 1 is kept.
    "redaction_regex": r"(\bu/|/user/|overview\\?_for\\?_)(?:\\?_|[A-Za-z0-9-]){3,}",
    "redaction_replacement": r"\1[user]",
    "exclusions": {
        "natmed": {"nav_or_boilerplate": ["preamble", "references"]},
        "dsld": {
            # Case- and punctuation-insensitive whole text; checked before the other rules.
            "bare_heading_text": ["ingredients", "dietary supplement", "supplement"],
            "fda_disclaimer_boilerplate": ["FDA Disclaimer Statement"],
            "administrative_label_text": {
                "always": ["General: Product/Version Code", "Seals/Symbols"],
                "if_ip_regex": ["Brand IP Statement(s) re: (c), (TM), (SM)"],
                "ip_regex": r"©|®|™|\(c\)|\(r\)|\(tm\)|copyright|trademark|registered|patent|all rights reserved",
                "keep_if_safety_regex": r"warning|caution|do not|don't|tamper|safety seal"
                                        r"|seal is (broken|missing)|allerg|pregnan|nursing|keep out of"
                                        r"|consult|physician|doctor|overdose|serving|dosage|maximum|stack",
            },
        },
        "reddit": {
            "bot_message": [
                # Moderator bots and bot-sleuth-bot; 173 passages.
                r"I am a bot[,.]? (and )?th(is|e) action was performed automatically",
                # sneakpeekbot ("... using the top posts of the year! ... I'm a bot, beep boop"); 1 passage.
                r"^Here's a sneak peek of /r/\w+ using the top posts",
            ],
            "removed_or_empty": r"\[\s*(deleted|removed)(\s+by\s+reddit)?\s*\]",
            "very_short_reply": "comment under very_short_text_words with mention_scope thread_context",
        },
    },
    "terminology": "scripts/prepare_terminology_lookup.py build_terminology; propose_candidates_only",
}
MAX_TOKENS = CONFIG["max_tokens"]
MAX_CONTEXT = CONFIG["max_context_tokens"]
TERMINAL = re.compile(CONFIG["terminal_word_regex"])
USERNAME = re.compile(CONFIG["username_regex"])
REDACTION = re.compile(CONFIG["redaction_regex"])
ADMIN = CONFIG["exclusions"]["dsld"]["administrative_label_text"]


# ---------------------------------------------------------------- helpers

def sha256(data):
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def file_sha(path):
    return sha256(Path(path).read_bytes())


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def require(condition, message):
    if not condition:
        raise SystemExit(f"ERROR: {message}")


def jsonl_bytes(rows):
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows).encode()


# ---------------------------------------------------------------- tokenizer

def load_tokenizer(directory):
    """Load the pinned tokenizer, downloading missing files; hashes are always verified."""
    spec = CONFIG["tokenizer"]
    require("tokenizers==" + tokenizers.__version__ == spec["library"], f"need {spec['library']}")
    directory.mkdir(parents=True, exist_ok=True)
    for name, expected in spec["files"].items():
        path = directory / name
        if not path.exists():
            url = f"https://huggingface.co/{spec['model']}/resolve/{spec['revision']}/{name}"
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
            require(sha256(data) == expected, f"downloaded {name} does not match its pinned hash")
            path.write_bytes(data)
        require(file_sha(path) == expected, f"{path} does not match its pinned hash")
    tok = Tokenizer.from_file(str(directory / "tokenizer.json"))
    tok.no_truncation()
    tok.no_padding()
    return tok


# ---------------------------------------------------------------- graph

class Graph:
    """The parts of the frozen export needed here, after hash verification."""

    def __init__(self, directory):
        self.dir = directory
        self.manifest_sha = file_sha(directory / "manifest.json")
        self.file_hashes = json.loads((directory / "manifest.json").read_text())["files"]
        self.verify()

        self.passages = self.nodes("SourcePassage")
        self.statements = {i: n for i, n in self.nodes("LabelAssertion").items()
                           if n[0]["kind"] == "label_statement"}
        self.labels = self.nodes("ProductLabel")
        self.occurrences = self.nodes("IngredientOccurrence")
        self.claims = self.nodes("ClinicalClaim")
        self.monographs = self.nodes("Monograph")
        self.posts = self.nodes("RedditPost")
        self.comments = self.nodes("RedditComment")
        self.topics = {i: p["name"] for i, (p, _) in self.nodes("SupplementTopic").items()}

        # edges[type][start_id] -> list of end ids
        self.edges = defaultdict(lambda: defaultdict(list))
        with (directory / "relationships/relationships.csv").open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                self.edges[row["type"]][row["start_id"]].append(row["end_id"])

        self.evidence = {}
        with (directory / "provenance/evidence.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                self.evidence[row["id"]] = row

    def verify(self):
        """Every file listed in the graph manifest must still match it."""
        require(file_sha(self.dir / "manifest.json") == self.manifest_sha, "graph manifest changed")
        for name, expected in self.file_hashes.items():
            require(file_sha(self.dir / name) == expected, f"graph file changed: {name}")

    def nodes(self, kind):
        """{node id: (properties, evidence ids)}"""
        with (self.dir / "nodes" / f"{kind}.csv").open(newline="", encoding="utf-8") as fh:
            return {r["id"]: (json.loads(r["properties_json"]), json.loads(r["evidence_ids"]))
                    for r in csv.DictReader(fh)}

    def one(self, edge_type, start):
        """Single target of an edge, or None."""
        targets = self.edges[edge_type].get(start, [])
        require(len(targets) <= 1, f"{start} has several {edge_type} edges")
        return targets[0] if targets else None

    def topic_names(self, edge_types, starts):
        return sorted({self.topics[t] for e in edge_types for s in starts
                       for t in self.edges[e].get(s, [])})


# ---------------------------------------------------------------- text handling

class SourceWindow:
    """A whitespace-normalized passage located in its raw source text by word index."""

    def __init__(self, source_text, text, word_start):
        words = list(re.finditer(r"\S+", source_text))
        self.words = list(re.finditer(r"\S+", text))
        end = word_start + len(self.words)
        self.source_words = words[word_start:end]
        require(self.words and [w.group() for w in self.source_words] == text.split(),
                f"passage text does not match its source window: {text[:60]!r}")
        self.previous_word = words[word_start - 1].group() if word_start else None
        self.has_following = end < len(words)

    def source_range(self, start, end):
        """Raw source range of passage characters [start, end), ignoring edge whitespace."""
        pairs = [(w, s) for w, s in zip(self.words, self.source_words)
                 if w.end() > start and w.start() < end]
        (first, first_source), (last, last_source) = pairs[0], pairs[-1]
        return (first_source.start() + max(0, start - first.start()),
                last_source.end() - max(0, last.end() - end))


def raw_line_headings(raw):
    """Drug headings of a "nutrient depletions" section, which has no claims.

    Every entry in these sections is laid out as whole lines: DRUG NAME / "Depletion Rating" /
    MAJOR|MODERATE|INSIGNIFICANT / advice / explanation. A line is a heading only if the next two
    lines are that marker and a known rating, and it is short without final punctuation. The whole
    section must fit the layout (first line is a heading, every marker belongs to one), otherwise
    nothing is used. Each heading spans to the next heading.
    """
    rule = CONFIG["natmed_raw_line_headings"]
    lines = list(re.finditer(r"[^\n]+", raw))
    found = [line for line, marker, rating in zip(lines, lines[1:], lines[2:])
             if marker.group() == rule["marker_line"] and rating.group() in rule["rating_lines"]
             and len(line.group()) <= rule["max_heading_chars"]
             and not TERMINAL.search(line.group())]
    if not found or found[0].start() != 0 \
            or len(found) != sum(line.group() == rule["marker_line"] for line in lines):
        return []
    ends = [line.start() for line in found[1:]] + [len(raw)]
    return [{"id": None, "start": line.start(), "end": end, "heading": line.group(), "rating": None}
            for line, end in zip(found, ends)]


def headings_in(entries, a, b):
    """Headings for a raw range: the one still active at its start, then those beginning inside."""
    active = max((e for e in entries if e["start"] < a < e["end"]),
                 key=lambda e: (e["start"], e["id"] or ""), default=None)
    inside = sorted((e for e in entries if a <= e["start"] < b),
                    key=lambda e: (e["start"], e["id"] or ""))
    ordered = ([(active, True)] if active else []) + [(e, False) for e in inside]
    return [{"heading": e["heading"], "claim_id": e["id"], "continued": continued,
             "rating": e["rating"]} for e, continued in ordered if e["heading"]]


def heading_context(tok, base, headings):
    """Append headings to base, dropping whole headings from the end over the context cap.

    Returns (context, headings kept, whether any were dropped).
    """
    kept = []
    for h in headings:  # consecutive equal headings are shown once
        if not kept or kept[-1]["heading"] != h["heading"]:
            kept.append(h)
    shown = len(kept)
    while kept:
        listed = "; ".join(h["heading"] + (" (continued)" if h["continued"] else "") for h in kept)
        context = f"{base} | {listed}"
        if len(tok.encode(context, add_special_tokens=False).ids) <= MAX_CONTEXT:
            return context, kept, len(kept) < shown
        kept.pop()
    return base, kept, shown > 0


def redact(text):
    return REDACTION.sub(CONFIG["redaction_replacement"], text)


def snippet_context(tok, base, snippet):
    """Join base + parent snippet; drop trailing snippet words if the context is too long.

    Returns (context, shortened, snippet kept). The base is never shortened.
    """
    def size(value):
        return len(tok.encode(value, add_special_tokens=False).ids)

    context = f"{base} | Replying to: {snippet}"
    if size(context) <= MAX_CONTEXT:
        return context, False, True
    words = snippet.removesuffix("…").split()
    while len(words) > 1:
        words.pop()
        context = f"{base} | Replying to: {' '.join(words)}…"
        if size(context) <= MAX_CONTEXT:
            return context, True, True
    return base, True, False


def split_text(text, tokens):
    """Contiguous (start, end) ranges covering text, each within the limit by tokens(start, end)."""
    def fits(start, end):
        return tokens(start, end) <= MAX_TOKENS

    if fits(0, len(text)):
        return [(0, len(text))]
    # Cuts fall after a whitespace run, so the whitespace stays with the preceding part.
    sentence_cuts, space_cuts = [], []
    for m in re.finditer(r"\s+", text):
        is_sentence = "\n" in m.group() or TERMINAL.search(text[:m.start()])
        (sentence_cuts if is_sentence else space_cuts).append(m.end())
    parts, start = [], 0
    while not fits(start, len(text)):
        for cuts in (sentence_cuts, space_cuts, range(start + 1, len(text))):
            cut = next((c for c in reversed(cuts)
                        if c > start and text[start:c].strip() and fits(start, c)), None)
            if cut:
                break
        require(cut, f"context leaves no room for text: {text[:80]!r}")
        parts.append((start, cut))
        start = cut
    parts.append((start, len(text)))
    return parts


# ---------------------------------------------------------------- chunk assembly

def build_chunks(tok, record, text, describe, *, window=None):
    """Turn one KG text into one or more chunk rows.

    `record` holds the fields shared by all parts. `describe(start, end, text)` returns the fields
    that depend on a part's own span: context, bm25_context, flags, extra and, for NatMed, links.
    """
    def encode(start, end):
        context = describe(start, end, text[start:end])["context"]
        return tok.encode(context, index_text(text[start:end])).ids

    def index_text(part):
        return redact(part) if record["source"] == "reddit" else part

    parts = split_text(text, lambda start, end: len(encode(start, end)))
    rows = []
    for index, (start, end) in enumerate(parts):
        part = text[start:end]
        fields = describe(start, end, part)
        words = part.split()
        flags = set(fields.pop("flags"))
        if len(words) < CONFIG["short_text_words"]:
            flags.add("short_text")
        if len(words) < CONFIG["very_short_text_words"]:
            flags.add("very_short_text")
        if len(parts) > 1:
            flags.add("split")
        # Punctuation screening signal only, not a verified sentence boundary.
        before = text[:start].split()[-1] if index else (window and window.previous_word)
        if before and not TERMINAL.search(before):
            flags.add("starts_mid_sentence")
        following = index < len(parts) - 1 or (window and window.has_following)
        if following and not TERMINAL.search(words[-1]):
            flags.add("ends_mid_sentence")
        if USERNAME.search(part):
            flags.add("contains_username_mention")
        if record["topics_inherited"] and not record["topics_direct"]:
            flags.add("inherited_topic_only")
        indexed = index_text(part)
        if indexed != part:
            flags.add("username_redacted")
        rows.append({
            **record, **fields,
            "chunk_id": f"{record['kg_node_id']}#p{index}",
            "text": part,
            "index_text": indexed,
            "text_sha256": sha256(part),
            "embedding_input_sha256": sha256(fields["context"] + "\x00" + indexed),
            "token_count": len(encode(start, end)),
            "part_index": index,
            "part_count": len(parts),
            "part_char_start": start,
            "part_char_end": end,
            "index_default": record["index_exclusion_reason"] is None,
            "flags": flags,
        })
    return rows


def finish(rows):
    """Add duplicate counts, neighbours and the final order for one source."""
    counts = Counter(r["text_sha256"] for r in rows)
    sequences = defaultdict(list)
    for row in rows:
        row["duplicate_text_count"] = counts[row["text_sha256"]]
        if row["duplicate_text_count"] > 1:
            row["flags"].add("repeated_text")
        row["flags"] = sorted(row["flags"])
        span = row["source_span"]
        if span:  # passages: neighbours within the same source record and section
            key, order = (row["parent_node_id"], span["section_index"]), span["word_start"]
        else:  # label statements: only parts of the same statement
            key, order = row["kg_node_id"], 0
        sequences[key].append((order, row["part_index"], row))
    for sequence in sequences.values():
        ordered = [row for *_, row in sorted(sequence, key=lambda s: s[:2])]
        for i, row in enumerate(ordered):
            row["prev_chunk_id"] = ordered[i - 1]["chunk_id"] if i else None
            row["next_chunk_id"] = ordered[i + 1]["chunk_id"] if i + 1 < len(ordered) else None
    return sorted(rows, key=lambda r: (r["kg_node_id"], r["part_index"]))


def review_status(requires_review, claim_states=()):
    return {"clinical_approval": False, "requires_clinical_review": requires_review,
            "claim_review_states": sorted(set(claim_states))}


# ---------------------------------------------------------------- sources

def lookup(fields, dotted):
    """Value of a dotted field path, or None."""
    for key in dotted.split(".") if dotted else []:
        fields = fields[key]
    return fields if dotted else None


def natmed_claims(g, records):
    """{(record id, section index): claims with trimmed raw spans and their verbatim headings}"""
    claims = defaultdict(list)
    for claim_id, (p, _) in g.claims.items():
        span, fields = p["source_span"], p["original_fields"]
        section_index = int(re.fullmatch(r"/\d+/sections/(\d+)/text", span["pointer"]).group(1))
        raw = records[p["record_id"]]["sections"][section_index]["text"]
        excerpt = raw[span["start"]:span["end"]]
        kind = fields["claim_type"]
        heading = lookup(fields, CONFIG["natmed_heading_fields"].get(kind))
        if not heading and kind == "interaction" \
                and fields["source"]["section_heading"] == "interactions with conditions":
            heading = fields["population"]
        claims[p["record_id"], section_index].append({
            "id": claim_id, "type": kind, "heading": heading or None, "state": p["review_state"],
            "rating": lookup(fields, CONFIG["natmed_rating_fields"].get(kind)),
            "start": span["end"] - len(excerpt.lstrip()), "end": span["start"] + len(excerpt.rstrip())})
    return claims


def natmed_chunks(g, tok, records):
    """SourcePassage nodes of NatMed monographs, linked to the pending claims they overlap."""
    claims_by_section = natmed_claims(g, records)
    rows = []
    for node_id, (p, evidence_ids) in g.passages.items():
        if p["source"] != "natmedpro":
            continue
        f = p["original_fields"]
        monograph = g.one("PASSAGE_OF", node_id)
        raw = records[f["record_id"]]["sections"][f["section_index"]]["text"]
        window = SourceWindow(raw, f["text"], f["word_start"])
        claims = claims_by_section[f["record_id"], f["section_index"]]
        is_depletion = f["section"] == CONFIG["natmed_raw_line_headings"]["section"]
        entries = claims or (raw_line_headings(raw) if is_depletion else [])
        labels = {c["label"] for c in f["citation_links"]}

        def describe(start, end, part, f=f, window=window, claims=claims, entries=entries, labels=labels):
            a, b = window.source_range(start, end)
            linked = sorted((c for c in claims if c["start"] < b and a < c["end"]), key=lambda c: c["id"])
            headings = headings_in(entries, a, b)
            context, shown, shortened = heading_context(tok, f"{f['title']} | {f['section']}", headings)
            flags = {name for name, on in {
                "claim_split_across_passages": any(c["start"] < a or c["end"] > b for c in linked),
                "context_shortened": shortened,
                "heading_from_pending_claim": any(h["claim_id"] for h in shown),
                "heading_from_raw_line": any(h["claim_id"] is None for h in shown),
                "multi_heading": len({h["heading"] for h in headings}) > 1,
            }.items() if on}
            is_whole = (start, end) == (0, len(f["text"]))
            return {
                "context": context, "bm25_context": context, "flags": flags,
                "linked_node_ids": [c["id"] for c in linked],
                "review_status": review_status(f["requires_clinical_review"], (c["state"] for c in linked)),
                "extra": {
                    "citation_labels": sorted(
                        c for c in labels
                        if is_whole or re.search(rf"(?<!\w){re.escape(c)}(?!\w)", part)),
                    "source_updated_at": f["source_updated_at"],
                    "source_char_start": a, "source_char_end": b,
                    "headings": headings,
                    "linked_claims": [{
                        "claim_id": c["id"], "claim_type": c["type"], "heading": c["heading"],
                        "review_state": c["state"],
                        "fully_in_passage": a <= c["start"] and c["end"] <= b} for c in linked],
                },
            }

        boilerplate = CONFIG["exclusions"]["natmed"]["nav_or_boilerplate"]
        rows += build_chunks(tok, {
            "source": "natmed", "evidence_role": p["evidence_role"],
            "kg_node_id": node_id, "kg_node_type": "SourcePassage",
            "parent_node_id": monograph, "parent_node_type": "Monograph",
            "evidence_ids": evidence_ids, "source_pointer": p["provenance"],
            "source_url": f["source_url"] or None, "title": f["title"], "section": f["section"],
            "topics_direct": g.topic_names(["HAS_SOURCE_TOPIC"], [monograph]), "topics_inherited": [],
            "index_exclusion_reason": "nav_or_boilerplate" if f["section"] in boilerplate else None,
            "source_span": {"section_index": f["section_index"], "word_start": f["word_start"],
                            "word_end": f["word_start"] + len(window.words)},
        }, f["text"], describe, window=window)
    return finish(rows)


def reddit_exclusion(text, very_short_reply):
    rules = CONFIG["exclusions"]["reddit"]
    if any(re.search(pattern, text, re.I) for pattern in rules["bot_message"]):
        return "bot_message"
    if re.fullmatch(rules["removed_or_empty"], text.strip(), re.I) or not any(c.isalnum() for c in text):
        return "removed_or_empty"
    return "very_short_reply" if very_short_reply else None


def reddit_chunks(g, tok):
    """SourcePassage nodes of Reddit posts and comments (user reports)."""
    rows = []
    for node_id, (p, evidence_ids) in g.passages.items():
        if p["source"] != "reddit":
            continue
        f = p["original_fields"]
        parent = g.one("PASSAGE_OF", node_id)
        is_post = parent in g.posts
        record = (g.posts if is_post else g.comments)[parent][0]["original_fields"]
        # Record text in the KG is identical to the raw Reddit text, so it serves as source text.
        window = SourceWindow(record["text"], f["text"], f["word_start"])
        record_words = len(record["text"].split())
        thread = g.one("IN_THREAD", parent)
        reply_to = g.one("REPLY_TO", parent)
        title = g.posts[thread][0]["original_fields"]["title"] if thread else None

        flags = set()
        if is_post:
            base = f"Reddit post | {title}"
        elif thread:
            base = f"Reddit comment | Thread: {title}"
        else:
            base = f"Reddit comment | r/{record['subreddit']}"
            flags.add("thread_title_missing")
        clean_base = context = redact(base)
        redacted = clean_base != base
        if not is_post and reply_to in g.comments and record_words < CONFIG["short_comment_words"]:
            parent_words = g.comments[reply_to][0]["original_fields"]["text"].split()
            limit = CONFIG["parent_snippet_words"]
            snippet = " ".join(parent_words[:limit]) + ("…" if len(parent_words) > limit else "")
            context, shortened, kept = snippet_context(tok, clean_base, redact(snippet))
            redacted = redacted or (kept and redact(snippet) != snippet)
            if kept:
                flags.add("parent_snippet_in_context")
            if shortened:
                flags.add("context_shortened")
        if redacted:
            flags.add("username_redacted")

        require(f["mention_scope"] in ("own_text", "thread_context"), f"mention scope of {node_id}")
        direct = f["mention_scope"] == "own_text"
        terms = {s["supplement"]: s["matched_terms"] for s in f["supplements"]}
        topics = sorted(terms)

        def describe(start, end, part, f=f, window=window, record=record, flags=flags, context=context,
                     bm25=clean_base, terms=terms if direct else {}):
            a, b = window.source_range(start, end)
            return {
                "context": context, "bm25_context": bm25, "flags": flags,
                "extra": {
                    "record_type": f["record_type"], "subreddit": record["subreddit"],
                    "thread_id": f["thread_id"], "parent_id": f["parent_id"],
                    "mention_scope": f["mention_scope"], "source_created_at": f["source_created_at"],
                    "source_char_start": a, "source_char_end": b,
                    "topics_in_text": sorted(
                        topic for topic, names in terms.items()
                        if any(re.search(rf"(?<!\w){re.escape(n)}(?!\w)", part, re.I) for n in names)),
                },
            }

        very_short_reply = not is_post and not direct and record_words < CONFIG["very_short_text_words"]
        rows += build_chunks(tok, {
            "source": "reddit", "evidence_role": p["evidence_role"],
            "kg_node_id": node_id, "kg_node_type": "SourcePassage",
            "parent_node_id": parent, "parent_node_type": "RedditPost" if is_post else "RedditComment",
            # A post's IN_THREAD edge points to itself; the parent node is not repeated as a link.
            "linked_node_ids": sorted({n for n in (thread, reply_to) if n} - {parent}),
            "evidence_ids": evidence_ids, "source_pointer": p["provenance"],
            "source_url": f["source_url"] or None, "title": title, "section": f["section"],
            "topics_direct": topics if direct else [], "topics_inherited": [] if direct else topics,
            "review_status": review_status(f["requires_clinical_review"]),
            "index_exclusion_reason": reddit_exclusion(f["text"], very_short_reply),
            "source_span": {"section_index": f["section_index"], "word_start": f["word_start"],
                            "word_end": f["word_start"] + len(window.words)},
        }, f["text"], describe, window=window)
    return finish(rows)


def dsld_exclusion(statement_type, text):
    rules = CONFIG["exclusions"]["dsld"]
    if " ".join(re.findall(r"\w+", text.casefold())) in rules["bare_heading_text"]:
        return "bare_heading_text"
    if statement_type in rules["fda_disclaimer_boilerplate"]:
        return "fda_disclaimer_boilerplate"
    administrative = statement_type in ADMIN["always"] or (
        statement_type in ADMIN["if_ip_regex"] and re.search(ADMIN["ip_regex"], text, re.I))
    if administrative and not re.search(ADMIN["keep_if_safety_regex"], text, re.I):
        return "administrative_label_text"
    return None


def dsld_chunks(g, tok):
    """LabelAssertion nodes that are verbatim label statements."""
    label_of = {a: label for label, assertions in g.edges["HAS_ASSERTION"].items() for a in assertions}

    def is_other(occurrence):
        """Declared as an other ingredient, or nested under one."""
        while occurrence:
            p = g.occurrences[occurrence][0]
            if "other_ingredient" in (p["role"], p["interpreted_role"]):
                return True
            occurrence = p["parent_id"]
        return False

    rows = []
    for node_id, (p, evidence_ids) in g.statements.items():
        label = label_of[node_id]
        attrs = g.labels[label][0]["attributes"]
        f = p["original_fields"]
        require(len(evidence_ids) == 1, f"{node_id} has several evidence rows")
        evidence = g.evidence[evidence_ids[0]]
        require(evidence["snapshot_id"] == label, f"{node_id} evidence belongs to another label")
        pointer = evidence["locator"]["pointer"]
        name, brand = attrs["fullName"], attrs.get("brandName") or None
        context = f"{name} ({brand}) | {f['type']}" if brand else f"{name} | {f['type']}"
        context = re.sub(r"[\x00-\x1f\x7f\s]+", " ", context).strip()
        other, declared = [], []
        for occurrence in g.edges["DECLARES_OCCURRENCE"].get(label, []):
            (other if is_other(occurrence) else declared).append(occurrence)
        topic_edges = ["HAS_DECLARED_TOPIC", "INGREDIENT_NAME_MENTIONS_TOPIC"]
        fields = {
            "context": context, "bm25_context": context,
            "flags": {"off_market"} if attrs["offMarket"] else set(),
            "extra": {
                "brand": brand, "dsld_label_id": attrs["id"], "off_market": attrs["offMarket"],
                "statement_pointer": pointer,
                "declared_ingredient_topics": g.topic_names(topic_edges, declared),
                "other_ingredient_topics": g.topic_names(topic_edges, other),
            },
        }
        rows += build_chunks(tok, {
            "source": "dsld", "evidence_role": p["evidence_role"],
            "kg_node_id": node_id, "kg_node_type": "LabelAssertion",
            "parent_node_id": label, "parent_node_type": "ProductLabel",
            "linked_node_ids": [], "evidence_ids": evidence_ids,
            "source_pointer": {"file": f"data/raw/dsld/labels/label_{attrs['id']}.json",
                               "pointer": pointer, "sha256": g.labels[label][0]["payload_digest"]},
            "source_url": None, "title": name, "section": f["type"],
            "topics_direct": g.topic_names(["LABEL_TITLE_MENTIONS_TOPIC"], [label]),
            "topics_inherited": [], "review_status": review_status(None),
            "index_exclusion_reason": dsld_exclusion(f["type"], f["notes"]),
            "source_span": None,
        }, f["notes"], lambda start, end, part, fields=fields: dict(fields))
    return finish(rows)


# ---------------------------------------------------------------- checks and manifest

def verify_sources(source_hashes):
    for name, expected in source_hashes.items():
        require(file_sha(ROOT / name) == expected, f"raw source changed: {name}")


def check_chunks(g, source, rows, expected_nodes):
    """Structural checks that must hold before anything is written."""
    parts = defaultdict(list)
    for r in rows:
        parts[r["kg_node_id"]].append(r)
        require(r["token_count"] <= MAX_TOKENS, f"{r['chunk_id']} is over the token limit")
        require(all(e in g.evidence for e in r["evidence_ids"]), f"{r['chunk_id']} evidence missing")
        require(r["parent_node_id"] in {"Monograph": g.monographs, "RedditPost": g.posts,
                                        "RedditComment": g.comments, "ProductLabel": g.labels}
                [r["parent_node_type"]], f"{r['chunk_id']} parent missing")
    require(set(parts) == set(expected_nodes), f"{source}: source nodes are not all represented")
    for node_id, group in parts.items():
        p = expected_nodes[node_id][0]["original_fields"]
        require("".join(r["text"] for r in group) == (p["notes"] if source == "dsld" else p["text"]),
                f"{node_id}: parts do not reproduce the node text")


def source_stats(rows):
    tokens = sorted(r["token_count"] for r in rows)
    reasons = Counter(r["index_exclusion_reason"] for r in rows if r["index_exclusion_reason"])
    return {
        "nodes": len({r["kg_node_id"] for r in rows}),
        "chunks": len(rows),
        "split_nodes": len({r["kg_node_id"] for r in rows if r["part_count"] > 1}),
        "index_default": sum(r["index_default"] for r in rows),
        "by_flag": dict(sorted(Counter(f for r in rows for f in r["flags"]).items())),
        "by_exclusion": dict(sorted(reasons.items())),
        "token_count": {"min": tokens[0], "median": statistics.median(tokens),
                        "p95": tokens[int(0.95 * (len(tokens) - 1))], "max": tokens[-1]},
    }


def terminology_stats(entries):
    return {"entries": len(entries),
            "by_source": dict(sorted(Counter(e["source"] for e in entries).items())),
            "by_flag": dict(sorted(Counter(f for e in entries for f in e["flags"]).items())),
            "with_ambiguous_names": sum(bool(e["ambiguous_names"]) for e in entries),
            "with_lookup_names": sum(bool(e["lookup_names"]) for e in entries),
            "with_ambiguous_lookup_names": sum(bool(e["ambiguous_lookup_names"]) for e in entries)}


def publish(output_root, version, files):
    """Write to a temporary directory, then move into place; an existing version must be identical."""
    output_root.mkdir(parents=True, exist_ok=True)
    target = output_root / version
    if target.exists():
        for name, data in files.items():
            path = target / name
            require(path.exists() and path.read_bytes() == data,
                    f"{path} exists with different content for the same version")
        return target, False
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=output_root))
    try:
        staging.chmod(0o755)
        for name, data in files.items():
            (staging / name).parent.mkdir(parents=True, exist_ok=True)
            (staging / name).write_bytes(data)
        staging.rename(target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return target, True


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-root", type=Path, default=Path("data/retrieval"))
    parser.add_argument("--tokenizer-dir", type=Path, default=Path(".cache/medcpt_tokenizer"))
    args = parser.parse_args()  # relative paths resolve against the repository root
    try:
        from prepare_terminology_lookup import build_terminology
    except ModuleNotFoundError as error:
        if error.name != "prepare_terminology_lookup":
            raise
        raise SystemExit("ERROR: scripts/prepare_terminology_lookup.py is required") from None

    csv.field_size_limit(10**8)
    tok = load_tokenizer(ROOT / args.tokenizer_dir)
    graph = Graph(ROOT / GRAPH)

    # NatMed raw sections are needed for character offsets; claims pin the expected file hash.
    pinned = {p["source_span"]["sha256"] for p, _ in graph.claims.values()
              if p["source_span"]["file"] == NATMED_RAW}
    require(len(pinned) == 1, "claims disagree about the NatMed source hash")
    source_hashes = {NATMED_RAW: pinned.pop()}
    verify_sources(source_hashes)
    lines = (ROOT / NATMED_RAW).read_text(encoding="utf-8").split("\n")
    records = {r["id"]: r for r in map(json.loads, filter(str.strip, lines))}

    chunks = {"natmed": natmed_chunks(graph, tok, records),
              "dsld": dsld_chunks(graph, tok),
              "reddit": reddit_chunks(graph, tok)}
    expected = {"dsld": graph.statements,
                "natmed": {i: n for i, n in graph.passages.items() if n[0]["source"] == "natmedpro"},
                "reddit": {i: n for i, n in graph.passages.items() if n[0]["source"] == "reddit"}}
    for source, rows in chunks.items():
        check_chunks(graph, source, rows, expected[source])
        for r in rows:
            pointer = r["source_pointer"]
            known = source_hashes.setdefault(pointer["file"], pointer["sha256"])
            require(known == pointer["sha256"], f"conflicting hashes for {pointer['file']}")
    verify_sources(source_hashes)

    entries = sorted(build_terminology(graph.dir, tok), key=lambda e: e["kg_node_id"])
    # Every node keeps its own entry; a repeated id would break lookups.
    require(len({e["entry_id"] for e in entries}) == len(entries), "duplicate terminology entry ids")
    require(all(i in graph.evidence for e in entries for i in e["evidence_ids"]),
            "terminology evidence missing")

    files = {f"{s}/chunks.jsonl": jsonl_bytes(rows) for s, rows in chunks.items()}
    files["terminology/entries.jsonl"] = jsonl_bytes(entries)
    outputs = {name: sha256(data) for name, data in sorted(files.items())}
    identity = {"graph_manifest_sha256": graph.manifest_sha, "config": CONFIG, "outputs": outputs}
    version = "indexing-inputs-v1-" + sha256(canonical(identity))[:20]
    stats = {s: source_stats(rows) for s, rows in chunks.items()}
    stats["terminology"] = terminology_stats(entries)
    manifest = {
        "corpus_version": version,
        "generator": "scripts/prepare_indexing_inputs.py",
        "graph": {"path": GRAPH, "manifest_sha256": graph.manifest_sha},
        # Every file read: graph export (plus its manifest above), raw sources, tokenizer.
        "inputs": {"graph_files": graph.file_hashes, "source_files": source_hashes,
                   "tokenizer_files": CONFIG["tokenizer"]["files"]},
        "tokenizer": CONFIG["tokenizer"], "config": CONFIG,
        "sources": stats, "outputs": outputs,
    }
    files["corpus_manifest.json"] = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    target, created = publish(ROOT / args.output_root, version, files)

    # Nothing read above may have changed, and what is on disk must be what was hashed.
    graph.verify()
    verify_sources(source_hashes)
    for name, data in files.items():
        require((target / name).read_bytes() == data, f"written file differs: {name}")

    for source, s in stats.items():
        print(source, json.dumps(s))
    print("inputs unchanged; output", "written to" if created else "already present and identical at", target)


if __name__ == "__main__":
    main()
