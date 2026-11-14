"""Apply simple confidence rules to the saved pilot review, without approving mappings."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import io
import json

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'data/processed/identity/pilot-candidate-review-v1-f03a6ba885c074ba/review.json'
RULES = {
    'C1': {'confidence': 'High', 'action': 'eligible_for_use',
           'description': 'Saved review supports the explicitly proposed relationship; form and scope are compatible at that relationship level.'},
    'C2': {'confidence': 'Medium', 'action': 'pending_review',
           'description': 'Saved review identifies missing qualifiers or unresolved specificity; no relationship is promoted.'},
    'C3': {'confidence': 'Low', 'action': 'exclude_exact_match',
           'description': 'Saved review identifies conflicting form, preparation or entity scope for exact identity.'},
}

def assign(row):
    outcome, relation = row['outcome'], row['proposed_relation']
    if outcome == 'supported_for_review':
        if relation not in {'denotes_concept', 'exact_material_match'}:
            raise ValueError('Supported candidate requires an explicit supported relationship')
        rule = 'C1'
        assessed = relation
    elif outcome == 'needs_evidence':
        if relation is not None:
            raise ValueError('Unresolved candidate unexpectedly proposes a relationship')
        rule, assessed = 'C2', 'unresolved'
    elif outcome == 'incompatible_exact_match':
        if relation is not None:
            raise ValueError('Incompatible candidate unexpectedly proposes a relationship')
        rule, assessed = 'C3', 'exact_material_match'
    else:
        raise ValueError('Unknown review outcome: ' + outcome)
    return {**{k: row[k] for k in ['mapping_id', 'origin_occurrence_id', 'dsld_label_id',
            'ingredient', 'target_source', 'target_id', 'target_name', 'outcome',
            'proposed_relation', 'evidence_ids']},
            'confidence': RULES[rule]['confidence'], 'rule_id': rule,
            'action': RULES[rule]['action'], 'assessed_relation': assessed,
            'reason': row['rationale'], 'approval_applied': False}


def main():
    digest = lambda b: hashlib.sha256(b).hexdigest()
    protected = {p: digest(p.read_bytes()) for folder in ['data/raw', 'data/processed/poc',
                 str(REVIEW.parent.relative_to(ROOT))] for p in (ROOT/folder).rglob('*') if p.is_file()}
    source = json.loads(REVIEW.read_bytes())
    pilot = ROOT/'data/processed/poc'/source['pilot_build']
    assert digest((pilot/'manifest.json').read_bytes()) == source['pilot_manifest_sha256']
    pilot_manifest = json.loads((pilot/'manifest.json').read_bytes())
    spec = pilot_manifest['tables']['mapping_assertions']
    assert digest((pilot/spec['file']).read_bytes()) == spec['sha256']
    mappings = {r['id']: r for r in map(json.loads, (pilot/spec['file']).read_text().splitlines())}
    result = [assign(row) for row in source['reviews']]
    assert len(result) == len(mappings) == 40
    assert {r['mapping_id'] for r in result} == set(mappings)
    assert len({r['mapping_id'] for r in result}) == len(result)
    assert all(r['proposed_relation'] == old['proposed_relation'] for r, old in zip(result, source['reviews']))
    assert all(not r['approval_applied'] for r in result)
    # Check rejection of malformed/unknown review states rather than defaulting to High.
    for bad in [dict(source['reviews'][0], outcome='unknown'),
                dict(source['reviews'][0], outcome='supported_for_review', proposed_relation=None)]:
        try:
            assign(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid review state was accepted')
    summary = []
    for source_name in sorted({r['target_source'] for r in result}):
        counts = Counter(r['confidence'] for r in result if r['target_source'] == source_name)
        summary.append({'source': source_name, **{k: counts[k] for k in ['High', 'Medium', 'Low']}})
    payload = {'version': 'mapping-confidence-v1', 'input_review': str(REVIEW.relative_to(ROOT)),
               'input_sha256': digest(REVIEW.read_bytes()), 'script_sha256': digest(Path(__file__).read_bytes()),
               'scope': '40 bounded pilot candidates; confidence in the assessed relationship, not clinical reliability or a calibrated probability.',
               'policy': 'High is eligible for use only at its proposed relationship level. Medium remains pending. Low excludes exact matching only. No approval or KG activation is applied by this report.',
               'rules': RULES, 'counts': dict(Counter(r['confidence'] for r in result)),
               'by_source': summary, 'mappings': result,
               'validation': {'complete_coverage': True, 'relations_preserved': True,
                              'invalid_states_rejected': True, 'approvals_applied': 0}}
    assert all(digest(p.read_bytes()) == h for p, h in protected.items())
    payload['validation']['raw_pilot_and_review_unchanged'] = True
    raw = (json.dumps(payload, indent=2, ensure_ascii=False)+'\n').encode()
    output = ROOT/'data/processed/identity'/('mapping-confidence-v1-'+digest(raw)[:16])
    output.mkdir(parents=True, exist_ok=True)
    csv_file = io.StringIO(newline='')
    writer = csv.DictWriter(csv_file, fieldnames=[k for k in result[0] if k != 'evidence_ids'], extrasaction='ignore')
    writer.writeheader(); writer.writerows(result)
    for name, data in [('confidence.json', raw), ('confidence.csv', csv_file.getvalue().encode())]:
        path = output/name
        if path.exists():
            assert path.read_bytes() == data, 'Existing report must not be overwritten with different content'
        else:
            path.write_bytes(data)
    print(output.relative_to(ROOT))
    print(json.dumps(payload['counts']))
    return output

if __name__ == '__main__':
    main()
