"""Verify and partition a checked-out CSE573 dataset without rewriting JSONL records.
Usage: python3 scripts/import_cse573_datasets.py /path/to/CSE573
No upstream code is executed. Existing import destinations are never overwritten.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    args = parser.parse_args()
    source = args.checkout.resolve()
    project = Path(__file__).resolve().parents[1]
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    repo = 'https://github.com/ARYN26/CSE573.git'
    timestamp = datetime.now(timezone.utc).isoformat()
    dataset = source / 'datasets'
    upstream_manifest = json.loads((dataset / 'manifest.json').read_bytes())
    # Validate every archive and uncompressed payload before creating any outputs.
    decoded = {}
    for item in upstream_manifest['files']:
        name = item['archive']
        if Path(name).name != name:
            raise ValueError('Unexpected archive path')
        archive = (dataset / name).read_bytes()
        plain = gzip.decompress(archive)
        assert len(archive) == item['archive_bytes'] and sha(archive) == item['archive_sha256'], name
        assert len(plain) == item['bytes'] and sha(plain) == item['sha256'], name
        decoded[name] = plain
    def lines(name):
        return [(json.loads(line), line) for line in decoded[name].splitlines(keepends=True) if line.strip()]
    records = lines('records.jsonl.gz')
    passages = lines('passages.jsonl.gz')
    nodes = lines('kg_nodes.jsonl.gz')
    edges = lines('kg_edges.jsonl.gz')
    sources = {'natmed': 'natmedpro', 'reddit': 'reddit'}
    assert {r['source'] for r, _ in records} == set(sources)
    assert {r['source'] for r, _ in passages} == set(sources)
    assert len(records) == upstream_manifest['records']
    assert len(passages) == upstream_manifest['rag_passages']
    assert len({r['id'] for r, _ in records}) == len(records)
    assert len({r['id'] for r, _ in nodes}) == len(nodes)
    node_by_id = {r['id']: r for r, _ in nodes}
    assert all(e['source'] in node_by_id and e['target'] in node_by_id for e, _ in edges)
    raw_dir = project / 'data/raw'
    archive_dir = raw_dir / 'imports/cse573' / commit
    destinations = {key: raw_dir / folder for key, folder in sources.items()}
    for path in [archive_dir, *destinations.values()]:
        if path.exists():
            raise FileExistsError(f'Import destination already exists: {path}')
    plans = {}
    allocated_records = []
    allocated_passages = []
    allocated_edges = []
    for key, dest in destinations.items():
        source_records = [(r, line) for r, line in records if r['source'] == key]
        record_ids = {r['id'] for r, _ in source_records}
        source_passages = [(r, line) for r, line in passages if r['source'] == key]
        assert all(r['record_id'] in record_ids for r, _ in source_passages)
        source_node_ids = {r['id'] for r, _ in nodes if r.get('source') == key}
        source_edges = [(r, line) for r, line in edges if r['source'] in source_node_ids]
        needed_node_ids = source_node_ids | {r['target'] for r, _ in source_edges}
        source_nodes = [(r, line) for r, line in nodes if r['id'] in needed_node_ids]
        assert all(r.get('source') in (None, key) for r, _ in source_nodes)
        output_sets = {'records.jsonl': source_records,
                       'upstream_derived/passages.jsonl': source_passages,
                       'upstream_derived/kg_nodes.jsonl': source_nodes,
                       'upstream_derived/kg_edges.jsonl': source_edges}
        plans[key] = (dest, output_sets)
        allocated_records.extend(line for _, line in source_records)
        allocated_passages.extend(line for _, line in source_passages)
        allocated_edges.extend(line for _, line in source_edges)
    assert Counter(allocated_records) == Counter(line for _, line in records)
    assert Counter(allocated_passages) == Counter(line for _, line in passages)
    assert Counter(allocated_edges) == Counter(line for _, line in edges)
    archive_dir.mkdir(parents=True)
    shutil.copytree(dataset, archive_dir / 'datasets')
    for name in ['README.md', 'DATASET_SPEC.md', 'PROJECT_CONTEXT.md']:
        if (source / name).exists():
            shutil.copyfile(source / name, archive_dir / name)
    archive_manifest = {'source_repository': repo, 'source_commit': commit, 'imported_at_utc': timestamp,
        'upstream_archives_verified': len(upstream_manifest['files']),
        'preserved_files': {str(p.relative_to(archive_dir)): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
                            for p in archive_dir.rglob('*') if p.is_file()},
        'operation': 'Archive preservation and source-based partition only; no additional content preprocessing.'}
    (archive_dir / 'import_manifest.json').write_text(json.dumps(archive_manifest, indent=2) + '\n')
    summary = {}
    for key, (dest, output_sets) in plans.items():
        dest.mkdir(parents=True)
        output_metadata = {}
        for name, rows in output_sets.items():
            content = b''.join(line for _, line in rows)
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            assert target.read_bytes() == content
            output_metadata[name] = {'records': len(rows), 'bytes': len(content), 'sha256': sha(content),
                                     'original_jsonl_lines_preserved': True}
        record_counts = dict(Counter(r['record_type'] for r, _ in output_sets['records.jsonl']))
        manifest = {'source': key, 'source_repository': repo, 'source_commit': commit,
            'imported_at_utc': timestamp, 'upstream_archive_directory': str(archive_dir.relative_to(project)),
            'upstream_source_field': key, 'record_counts': record_counts, 'files': output_metadata,
            'upstream_processing': 'Source records were normalized and passages/MENTIONS graph derived by upstream authors.',
            'local_operation': 'Source partition only; original JSONL lines and metadata unchanged.',
            'shared_nodes': 'Referenced supplement nodes are copied unchanged into each source graph where needed.',
            'clinical_review': 'Upstream review and capture-quality flags are preserved; graph edges are not validated medical claims.'}
        (dest / 'collection_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        summary[key] = {'record_types': record_counts, 'files': output_metadata}
    print(json.dumps({'commit': commit, 'imported': summary}, indent=2))


if __name__ == '__main__':
    main()
