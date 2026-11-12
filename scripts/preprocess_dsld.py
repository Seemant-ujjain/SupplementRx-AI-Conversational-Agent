"""DSLD step 1: preserve label records, flag market status and repeated names.

No entity merging, ingredient flattening, dose conversion or clinical extraction.
Outputs are versioned by source fingerprint and rules version. Raw files are read-only.
"""
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

RULES_VERSION = 'dsld-label-inventory-v1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def build_label_inventory(labels, categories, source_hashes):
    groups = defaultdict(list)
    ids = [str(row['id']) for row in labels]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate DSLD label IDs must be resolved before processing')
    for label in labels:
        key = (label.get('brandName'), label.get('fullName'))
        if all(isinstance(value, str) and value.strip() for value in key):
            groups[key].append(str(label['id']))
    repeated = {}
    group_for_id = {}
    for (brand, name), members in sorted(groups.items()):
        if len(members) < 2:
            continue
        group_id = 'dsld:name-group:' + digest(json.dumps([brand, name], ensure_ascii=False).encode())[:20]
        repeated[group_id] = {'group_id': group_id, 'brand_name': brand, 'product_name': name,
                              'label_ids': sorted(members, key=int),
                              'review_status': 'pending', 'match_method': 'exact_brand_and_product_name'}
        for label_id in members:
            group_for_id[label_id] = group_id
    rows = []
    for label in sorted(labels, key=lambda row: int(row['id'])):
        label_id = str(label['id'])
        value = label.get('offMarket')
        status = ({0: 'on_market_in_source', 1: 'off_market_in_source'}.get(value, 'unknown')
                  if type(value) is int else 'unknown')
        flags = []
        if status == 'off_market_in_source': flags.append('historical_market_status')
        if status == 'unknown': flags.append('unknown_market_status')
        if label_id in group_for_id: flags.append('repeated_brand_product_name')
        rows.append({'id': 'dsld:label:' + label_id, 'dsld_id': label_id,
            'product_name': label.get('fullName'), 'brand_name': label.get('brandName'),
            'market_status': status, 'market_status_raw': value,
            'search_categories': categories.get(label_id, []),
            'name_group_id': group_for_id.get(label_id), 'review_flags': flags,
            'source': {'file': f'data/raw/dsld/labels/label_{label_id}.json',
                       'sha256': source_hashes[label_id]},
            'raw_label': label})
    return rows, list(repeated.values())


def preprocess(project_root):
    project = Path(project_root).resolve()
    raw = project / 'data/raw/dsld'
    collection_bytes = (raw / 'collection.json').read_bytes()
    manifest_bytes = (raw / 'collection_manifest.json').read_bytes()
    collection = json.loads(collection_bytes)
    manifest = json.loads(manifest_bytes)
    labels = collection['labels']
    source_hashes = {}
    for label in labels:
        label_id = str(label['id'])
        data = (raw / 'labels' / f'label_{label_id}.json').read_bytes()
        if json.loads(data) != label:
            raise ValueError(f'Combined and individual label differ: {label_id}')
        source_hashes[label_id] = digest(data)
    rows, groups = build_label_inventory(labels, manifest['category_matches'], source_hashes)
    if len(rows) != collection['record_count'] or len(rows) != manifest['labels_downloaded']:
        raise ValueError('Source record counts disagree')
    for row, label in zip(rows, sorted(labels, key=lambda r:int(r['id']))):
        if row['raw_label'] != label:
            raise ValueError('Source label content changed during processing')
    source_fingerprint = {'collection_sha256': digest(collection_bytes),
                          'manifest_sha256': digest(manifest_bytes), 'label_sha256': source_hashes}
    run_id = RULES_VERSION + '-' + digest(encode(source_fingerprint))[:16]
    output = project / 'data/processed/dsld' / run_id
    counts = Counter(row['market_status'] for row in rows)
    current = [row for row in rows if row['market_status'] == 'on_market_in_source']
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=['id','dsld_id','product_name','brand_name','market_status'])
    writer.writeheader()
    for row in current: writer.writerow({key:row[key] for key in writer.fieldnames})
    payloads = {
        'label_inventory.jsonl': b''.join((json.dumps(row,ensure_ascii=False)+'\n').encode() for row in rows),
        'on_market_label_index.csv': buffer.getvalue().encode(),
        'repeated_name_groups.json': encode(groups),
    }
    report = {'rules_version': RULES_VERSION, 'source_label_count':len(labels),
        'output_label_count':len(rows), 'market_status_counts':dict(counts),
        'repeated_name_groups':len(groups),
        'labels_in_repeated_name_groups':sum(len(g['label_ids']) for g in groups),
        'records_removed':0, 'records_merged':0, 'raw_label_content_preserved':True,
        'market_status_policy':'Preserve all labels. On-market index means offMarket=0 in this source snapshot, not verified current availability.',
        'repeated_name_policy':'Exact nonempty brand/product names flag review groups, never identity or automatic deduplication.',
        'ingredient_and_dose_processing':'Not performed; original fields remain inside raw_label.'}
    payloads['validation_report.json'] = encode(report)
    # A same-input rerun is read-only if outputs still match; edited outputs are protected.
    if output.exists():
        for name, data in payloads.items():
            if not (output/name).exists() or (output/name).read_bytes()!=data:
                raise ValueError(f'Existing output differs; refusing overwrite: {output/name}')
        saved = json.loads((output/'manifest.json').read_bytes())
        if saved['source_fingerprint'] != source_fingerprint:
            raise ValueError('Existing manifest does not match sources')
        for name,data in payloads.items():
            if saved['files'][name]['sha256']!=digest(data):
                raise ValueError('Existing output manifest hash mismatch')
        return output, report
    output.mkdir(parents=True)
    for name,data in payloads.items(): (output/name).write_bytes(data)
    result_manifest = {'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'rules_version':RULES_VERSION,'run_id':run_id,'source_fingerprint':source_fingerprint,
        'files':{name:{'bytes':len(data),'sha256':digest(data)} for name,data in payloads.items()},
        'summary':report}
    (output/'manifest.json').write_bytes(encode(result_manifest))
    return output, report


if __name__ == '__main__':
    directory, report = preprocess(Path(__file__).resolve().parents[1])
    print(directory)
    print(json.dumps(report, indent=2))
