"""Verify and partition a checked-out CSE573 dataset without rewriting JSONL records.
Usage: python3 scripts/import_cse573_datasets.py /path/to/CSE573
No upstream code is executed. Use --update to archive existing source folders
and activate a new, verified snapshot. Locally modified source files are protected.
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
import tempfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    parser.add_argument('--update', action='store_true', help='Preserve existing source folders before updating')
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
    clinical_manifest_path = dataset / 'clinical_claims_manifest.json'
    clinical_manifest = json.loads(clinical_manifest_path.read_bytes()) if clinical_manifest_path.exists() else None
    archive_specs = list(upstream_manifest['files']) + (clinical_manifest['files'] if clinical_manifest else [])
    for item in archive_specs:
        name = item['archive']
        if Path(name).name != name:
            raise ValueError('Unexpected archive path')
        archive = (dataset / name).read_bytes()
        plain = gzip.decompress(archive)
        assert len(archive) == item['archive_bytes'] and sha(archive) == item['archive_sha256'], name
        assert len(plain) == item['bytes'] and sha(plain) == item['sha256'], name
        decoded[name] = plain
    # These public-metadata exports are outside the upstream restore manifests.
    # Preserve them and fingerprint them locally; do not claim upstream hash verification.
    for name in ['pubmed_metadata.jsonl.gz']:
        if (dataset / name).exists():
            decoded[name] = gzip.decompress((dataset / name).read_bytes())
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
    if archive_dir.exists():
        raise FileExistsError(f'Snapshot already exists: {archive_dir}')
    previous = {}
    for key, path in destinations.items():
        if not path.exists():
            continue
        if not args.update:
            raise FileExistsError(f'Use --update to preserve and replace: {path}')
        previous[key] = json.loads((path / 'collection_manifest.json').read_bytes())
        for name, metadata in previous[key]['files'].items():
            if sha((path / name).read_bytes()) != metadata['sha256']:
                raise ValueError(f'Locally modified imported file: {path / name}')
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
    extra_files = {}
    if clinical_manifest:
        natmed_records = {r['id']: r for r, _ in plans['natmed'][1]['records.jsonl']}
        html_rows = lines('natmed_source_html.jsonl.gz')
        assert {r['record_id'] for r, _ in html_rows} == set(natmed_records)
        for row, _ in html_rows:
            assert sha(row['html'].encode()) == row['sha256'] == natmed_records[row['record_id']]['source_html_sha256']
        claims = lines('clinical_claims.jsonl.gz')
        assert len(claims) == clinical_manifest['claim_count']
        assert all(r['review']['state'] == 'pending' for r, _ in claims)
        assert clinical_manifest['approved_count'] == 0
        for claim, _ in claims:
            ref = claim['source']; record = natmed_records[ref['record_id']]
            assert ref['content_hash'] == record['content_hash']
            section = record['sections'][ref['section_index']]
            assert section['text'][ref['start']:ref['end']] == ref['excerpt']
        schema = (source / 'config/clinical_claim.schema.json').read_bytes()
        assert sha(canonical(json.loads(schema))) == clinical_manifest['inputs']['clinical_schema_sha256']
        assert sha(canonical(sorted((r for r, _ in records), key=lambda r: r['id']))) == clinical_manifest['inputs']['source_records_sha256']
        for row in natmed_records.values():
            for ref in row.get('reference_documents', []):
                assert sha(ref['text'].encode()) == ref['content_hash']
        extra_files = {
            'source_html.jsonl': decoded['natmed_source_html.jsonl.gz'],
            'upstream_derived/pending_clinical/clinical_claims.jsonl': decoded['clinical_claims.jsonl.gz'],
            'upstream_derived/pending_clinical/clinical_claims.sample.json': decoded['clinical_claims.sample.json.gz'],
            'upstream_derived/pending_clinical/clinical_extraction_report.json': decoded['clinical_extraction_report.json.gz'],
            'upstream_derived/pending_clinical/clinical_claims_manifest.json': clinical_manifest_path.read_bytes(),
            'upstream_derived/pending_clinical/clinical_claim.schema.json': schema,
        }
    if 'pubmed_metadata.jsonl.gz' in decoded:
        extra_files['upstream_derived/pubmed_metadata.jsonl'] = decoded['pubmed_metadata.jsonl.gz']
        extra_files['upstream_derived/pubmed_report.json'] = (dataset / 'pubmed_report.json').read_bytes()
    if 'reddit' in previous:
        old_reddit = (destinations['reddit'] / 'records.jsonl').read_bytes()
        new_reddit = b''.join(line for _, line in plans['reddit'][1]['records.jsonl'])
        assert old_reddit == new_reddit, 'Reddit source changed; review before updating'
    archive_dir.mkdir(parents=True)
    shutil.copytree(dataset, archive_dir / 'datasets')
    for name in ['README.md', 'DATASET_SPEC.md', 'PROJECT_CONTEXT.md', 'READINESS_AUDIT.md']:
        if (source / name).exists():
            shutil.copyfile(source / name, archive_dir / name)
    for name in ['config', 'evaluation']:
        if (source / name).exists():
            shutil.copytree(source / name, archive_dir / name)
    archive_manifest = {'source_repository': repo, 'source_commit': commit, 'imported_at_utc': timestamp,
        'upstream_archives_verified': len(archive_specs),
        'preserved_files': {str(p.relative_to(archive_dir)): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
                            for p in archive_dir.rglob('*') if p.is_file()},
        'operation': 'Archive preservation and source-based partition only; no additional content preprocessing.'}
    (archive_dir / 'import_manifest.json').write_text(json.dumps(archive_manifest, indent=2) + '\n')
    summary = {}
    staging = Path(tempfile.mkdtemp(prefix='.cse573-import-', dir=raw_dir))
    for key, (dest, output_sets) in plans.items():
        dest = staging / sources[key]
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
        if key == 'natmed':
            for name, content in extra_files.items():
                target = dest / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                output_metadata[name] = {'bytes': len(content), 'sha256': sha(content), 'upstream_content_preserved': True}
        record_counts = dict(Counter(r['record_type'] for r, _ in output_sets['records.jsonl']))
        manifest = {'source': key, 'source_repository': repo, 'source_commit': commit,
            'imported_at_utc': timestamp, 'upstream_archive_directory': str(archive_dir.relative_to(project)),
            'upstream_source_field': key, 'record_counts': record_counts, 'files': output_metadata,
            'upstream_processing': 'Source records were normalized and passages/MENTIONS graph derived by upstream authors.',
            'local_operation': 'Source partition only; original JSONL lines and metadata unchanged.',
            'shared_nodes': 'Referenced supplement nodes are copied unchanged into each source graph where needed.',
            'clinical_review': 'Upstream review and capture-quality flags are preserved; graph edges are not validated medical claims.'}
        if key in previous:
            manifest['supersedes_source_commit'] = previous[key]['source_commit']
        if key == 'natmed' and clinical_manifest:
            manifest['pending_clinical_claims'] = clinical_manifest['claim_count']
            manifest['approved_clinical_claims'] = 0
        (dest / 'collection_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        summary[key] = {'record_types': record_counts, 'files': output_metadata}
    # Activate only after all staged files pass their recorded checksums.
    for key in sources:
        path = staging / sources[key]
        metadata = json.loads((path / 'collection_manifest.json').read_bytes())
        for name, expected in metadata['files'].items():
            assert sha((path / name).read_bytes()) == expected['sha256']
    moved = []
    activated = []
    try:
        for key, destination in destinations.items():
            if destination.exists():
                backup = archive_dir / 'previous_local' / sources[key]
                backup.parent.mkdir(parents=True, exist_ok=True)
                destination.rename(backup)
                moved.append((backup, destination))
            (staging / sources[key]).rename(destination)
            activated.append(destination)
    except BaseException:
        for destination in reversed(activated):
            destination.rename(staging / destination.name)
        for backup, destination in reversed(moved):
            backup.rename(destination)
        raise
    staging.rmdir()
    print(json.dumps({'commit': commit, 'imported': summary}, indent=2))


if __name__ == '__main__':
    main()
