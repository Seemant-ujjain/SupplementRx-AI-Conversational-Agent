"""Search the supplement evidence from the command line.

  python scripts/search.py                                   # interactive: type questions
  python scripts/search.py "can I take magnesium with blood pressure meds"
  python scripts/search.py "melatonin for sleep" --source natmed -k 5 --full
  python scripts/search.py "iron and levothyroxine" --compare

Shows retrieved source text only. It does not generate answers or check safety.
"""
import argparse
import os
import re
import shutil
import textwrap

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # models are cached by build_search_index.py

import retrieval as R

HEADINGS = {"natmed": "NATMED  clinical reference (claims pending review)",
            "dsld": "DSLD  what product labels say (not proof it works)",
            "reddit": "REDDIT  user-reported experience (not evidence)"}
# Rough display labels for the rerank score, not calibrated; never use them as a safety or abstention rule.
STRONG_RERANK, WEAK_RERANK = 10, 0
MODES = ("bm25", "dense", "hybrid")
HELP = """Type a question, or a setting:
  :mode bm25|dense|hybrid   search method        :rerank on|off   cross-encoder rescoring
  :source natmed,dsld|all   where to search      :k N             results per source
  :full on|off              whole passage        :compare         last question, every method
  :ids on|off               show KG ids          :scores on|off  every score
  :quit"""


def snippet(text, query, width=420):
    """The stretch of the passage with the most query words, cut at word boundaries."""
    if len(text) <= width:
        return text
    terms = set(R.tokenize(query))
    words = list(re.finditer(r"\S+", text))
    best, best_score = 0, -1
    for i in range(0, len(words), 5):
        start = words[i].start()
        score = len(terms & set(R.tokenize(text[start:start + width])))
        if score > best_score:
            best, best_score = start, score
    part = text[best:best + width]
    end = best + len(part)
    if end < len(text):
        part = part.rsplit(None, 1)[0] + " …"
    return ("… " if best else "") + part


def match_label(score):
    if score >= STRONG_RERANK:
        return "strong"
    return "moderate" if score >= WEAK_RERANK else "weak, probably not relevant"


def describe(result, all_scores):
    """The rerank score with a plain label; BM25/dense places and points only when asked for or not reranked."""
    bits = []
    if result["rerank"] is not None:
        bits.append(f"match: {match_label(result['rerank'])} ({result['rerank']})")
    if all_scores or result["rerank"] is None:
        for method, (rank, score) in result["ranks"].items():
            bits.append(f"{method} #{rank}" + (f" ({score})" if all_scores else ""))
    return " · ".join(bits)


def show(results, query, settings):
    width = min(shutil.get_terminal_size((100, 24)).columns, 110)
    for source, hits in results.items():
        print(f"\n=== {HEADINGS[source]} " + "=" * max(0, width - len(HEADINGS[source]) - 5))
        if not hits:
            print("  no match")
        for n, result in enumerate(hits, 1):
            chunk = result["chunk"]
            scores = describe(result, settings["scores"])
            print(textwrap.fill(f"{n}. {chunk['context']}", width, subsequent_indent="   "))
            print(f"   [{scores}]")
            text = " ".join(chunk["index_text"].split())
            text = text if settings["full"] else snippet(text, query)
            print(textwrap.fill(text, width, initial_indent="   ", subsequent_indent="   "))
            notes = []
            if source == "natmed" and chunk["source_url"]:
                notes.append(chunk["source_url"])
            if source == "dsld":
                notes.append(f"DSLD label {chunk['extra']['dsld_label_id']}"
                             + (" (off market)" if "off_market" in chunk["flags"] else ""))
            if source == "reddit" and chunk["topics_inherited"]:
                notes.append("topic taken from the thread, not this comment: " + ", ".join(chunk["topics_inherited"]))
            if result["same_text"]:
                notes.append(f"same text in {len(result['same_text'])} more match(es)")
            if settings["ids"]:
                notes.append(f"chunk {chunk['chunk_id']} -> parent {chunk['parent_node_id']}")
            for note in notes:
                print(f"   ({note})")


def compare(searcher, query, settings):
    runs = [(m, m, False) for m in MODES] + [("hybrid+rerank", "hybrid", True)]
    for label, mode, rerank in runs:
        print(f"\n##### {label}")
        for source, hits in searcher.search(query, mode, settings["source"], settings["k"], rerank).items():
            for n, result in enumerate(hits, 1):
                text = " ".join(result["chunk"]["index_text"].split())
                print(f"  {source:<6} {n}. {result['chunk']['context'][:70]} :: {snippet(text, query, 90)}")


def answer(searcher, query, settings):
    show(searcher.search(query, settings["mode"], settings["source"], settings["k"], settings["rerank"]), query, settings)


def parse_sources(value):
    names = list(R.SOURCES) if value == "all" else [v.strip() for v in value.split(",")]
    if not names or set(names) - set(R.SOURCES):
        raise ValueError("sources are natmed, dsld, reddit or all")
    return names


def change_setting(command, settings):
    name, _, value = command[1:].partition(" ")
    value = value.strip()
    if name == "mode" and value in MODES:
        settings["mode"] = value
    elif name in ("rerank", "full", "ids", "scores") and value in ("on", "off"):
        settings[name] = value == "on"
    elif name == "source":
        settings["source"] = parse_sources(value)
    elif name == "k" and value.isdigit() and int(value) > 0:
        settings["k"] = int(value)
    else:
        raise ValueError(HELP)
    print("settings:", settings)


def interactive(searcher, settings):
    print(HELP)
    last = None
    while True:
        try:
            line = input("\nsearch> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if line in (":quit", ":q", "quit", "exit"):
            return
        if not line:
            continue
        try:
            if line == ":compare":
                if last:
                    compare(searcher, last, settings)
                else:
                    print("ask a question first")
            elif line.startswith(":"):
                change_setting(line, settings)
            else:
                last = line
                answer(searcher, line, settings)
        except ValueError as error:
            print(error)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query", nargs="?", help="leave out for interactive mode")
    parser.add_argument("--mode", choices=MODES, default="hybrid")
    parser.add_argument("--source", default="all", help="natmed,dsld,reddit or all")
    parser.add_argument("-k", type=int, default=3, help="results per source")
    parser.add_argument("--no-rerank", dest="rerank", action="store_false", help="skip cross-encoder rescoring (faster)")
    parser.add_argument("--compare", action="store_true", help="show every method side by side")
    parser.add_argument("--full", action="store_true", help="print whole passages")
    parser.add_argument("--ids", action="store_true", help="print chunk and KG ids")
    parser.add_argument("--scores", action="store_true", help="print BM25 and dense places and points too")
    args = parser.parse_args()
    if args.k < 1:
        parser.error("-k must be at least 1")
    try:
        sources = parse_sources(args.source)
    except ValueError as error:
        parser.error(str(error))
    settings = dict(mode=args.mode, source=sources, k=args.k, rerank=args.rerank, full=args.full, ids=args.ids,
                    scores=args.scores)
    searcher = R.Searcher()
    if not args.query:
        interactive(searcher, settings)
    elif args.compare:
        compare(searcher, args.query, settings)
    else:
        answer(searcher, args.query, settings)


if __name__ == "__main__":
    main()
