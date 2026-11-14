"""Reproduce an evidence-backed, assistant-authored scope review. No mapping approvals."""
import csv
import io
import json
from pathlib import Path
from audit_pubchem import resolve_path
from audit_mesh import bindings
from review_dsld_name_groups import snapshot, sha

VERSION = 'ingredient-scope-review-v2'
SEMANTICS = 'mapping-semantics-draft-v2'
SELECTION = {
    'alpha-linolenic acid': [65671, 80083],
    'lactobacillus acidophilus': [11613, 215449],
    'la-14 lactobacillus acidophilus': [177509],
    'lactobacillus acidophilus la14': [54155],
    'l. acidophilus dds-1': [259959, 260008],
    'turmeric root powder': [214296, 219999],
    'ashwagandha': [13653, 69019],
    'ashwagandha extract': [39970, 54522],
    'organic ashwagandha root powder': [25775],
    'creatine blend': [3714],
    'ashwagandha root extract & ashwagandha root powder blend': [74939, 74940],
    'probiotic blend': [11613, 32494],
}
# Curated interpretations of the inspected evidence, not a general-purpose classifier.
PROPOSALS = {
    ('alpha-linolenic acid', 'pubchem'): ('exact_material_match', 'needs_evidence', 'ING-02', 'Source identifies alpha-linolenic acid; target specifies all-Z stereochemistry. Saved aliases support the candidate, but confirm the designation bridge covers that specification before exact material acceptance.'),
    ('alpha-linolenic acid', 'rxnorm'): ('denotes_concept', 'needs_evidence', 'ING-02', 'Preferred name says linolenic acid; retain alpha/isomer specificity and check target meaning rather than dropping the qualifier.'),
    ('alpha-linolenic acid', 'mesh'): ('denotes_concept', 'supported_for_review', 'ING-02', 'Explicit alpha-linolenic source designation and category agree with the named descriptor; no quantity or material stereochemistry inference.'),
    ('lactobacillus acidophilus', 'rxnorm'): ('denotes_concept', 'supported_for_review', 'ING-06', 'Full species designation and bacterial context agree with the species-named target. Strain remains unknown.'),
    ('lactobacillus acidophilus', 'mesh'): ('denotes_concept', 'supported_for_review', 'ING-06', 'Full species designation and saved species definition support generic species meaning; not a strain, batch or viability match.'),
    ('la-14 lactobacillus acidophilus', 'rxnorm'): ('exact_material_match', 'supported_for_review', 'ING-07', 'Species and explicit LA-14 code agree despite word order/case. Match is at the named strain-designation level; no batch identity, viability or potency inference.'),
    ('turmeric root powder', 'rxnorm'): ('denotes_concept', 'supported_for_review', 'ING-04', 'Saved RxNorm Synonym explicitly bridges turmeric root powder to Curcuma longa root powder. Source preserves root and powder. Do not rewrite root as rhizome or infer extract.'),
    ('ashwagandha', 'mesh'): ('denotes_concept', 'needs_evidence', 'ING-04 ING-05', 'Source notes specify root, species and standardization; candidate has a broad name and no projected scope note. Need target definition before treating a specific source preparation as equivalent.'),
    ('ashwagandha extract', 'rxnorm'): ('exact_material_match', 'needs_evidence', 'ING-05', 'Source states root and a standardization percentage; target says whole extract. Saved names alone do not explain whole. Do not infer whole plant or assume the two scopes agree.'),
}
NO_TARGET = {
    'lactobacillus acidophilus la14': ('ING-07', 'No returned target. LA14 versus LA-14 is a possible alias to investigate, not an approved punctuation-normalization rule or a copied result from another query.'),
    'l. acidophilus dds-1': ('ING-07', 'No returned target. Preserve DDS-1 and abbreviated genus; do not substitute a generic species or another strain.'),
    'organic ashwagandha root powder': ('ING-04', 'No target. Preserve root/powder and marker information; an extract candidate from another query is not a replacement.'),
    'creatine blend': ('ING-08', 'No target; six nested ingredient declarations have NP quantities. A blend total does not establish proportions or assign the total to each child.'),
    'ashwagandha root extract & ashwagandha root powder blend': ('ING-08 ING-05', 'No target; named extract/powder blend and marker percentages do not establish their mixing proportions. Preserve markers instead of inventing component rows.'),
    'probiotic blend': ('ING-08', 'No target; shared ingredient registry ID does not establish the same component list or formulation. Preserve occurrence-specific nested ingredients.'),
}


def review(project):
    project = Path(project)
    before = snapshot(project / 'data/raw')
    root = project / 'data/processed/terminology/terminology-review-v1-34294732268f2352'
    manifest = json.loads((root / 'manifest.json').read_text())
    inputs = {}

    def checked(path, expected=None):
        data = path.read_bytes()
        actual = sha(data)
        if expected is not None and actual != expected:
            raise ValueError('Evidence changed: ' + str(path))
        inputs[str(path.relative_to(project))] = actual
        return data

    checked(root / 'manifest.json')
    terms = json.loads(checked(root / 'review.json', manifest['files']['review.json']['sha256']))
    occurrences = list(csv.DictReader(io.StringIO(checked(root / 'dsld_occurrences.csv', manifest['files']['dsld_occurrences.csv']['sha256']).decode())))
    queries = {q['query_key']: q for q in terms['queries']}
    collections = {s: json.loads(checked(project / m['file'], m['sha256'])) for s, m in manifest['inputs'].items()}
    mesh_path = manifest['inputs']['mesh']['file']
    category_target = next(c for c in queries['omega-3 fatty acids']['candidates']['mesh'] if c['source_id'] == 'D015525')
    hierarchy = []
    for i, b in enumerate(bindings(collections['mesh']['record_subgraph_responses'])):
        if (b['subject']['value'].endswith('/D017962') and b['predicate']['value'].endswith('#broaderDescriptor') and b['object']['value'].endswith('/D015525')):
            hierarchy.append({'source_file': mesh_path, 'locator_kind': 'rdf_statement', 'binding_index_in_flattened_subgraphs': i,
                              'statement': b})
    if not hierarchy:
        raise ValueError('Required alpha-linolenic/omega-3 hierarchy evidence absent')
    cases, rows = [], []
    for query, labels in SELECTION.items():
        q = queries[query]
        for label_id in labels:
            matches = [o for o in occurrences if o['query_key'] == query and o['dsld_id'] == str(label_id)]
            if len(matches) != 1:
                raise ValueError('Ambiguous selected source locator')
            origin = matches[0]
            label = json.loads(checked(project / origin['source_file'], origin['source_sha256']))
            occurrence = resolve_path(label, origin['json_path'])
            if occurrence['name'] != origin['name'] or str(occurrence['ingredientId']) != origin['ingredient_id']:
                raise ValueError('Source occurrence mismatch')
            case_id = f'case-{len(cases)+1:02d}'
            candidates = []
            for source, targets in q['candidates'].items():
                for target in targets:
                    item = {'source': source, 'collection_file': manifest['inputs'][source]['file'], **target}
                    if source == 'rxnorm':
                        props = collections[source]['records'][str(target['source_id'])]['all_properties']['response'].get('propConceptGroup', {}).get('propConcept', [])
                        item['saved_name_properties'] = [dict(v, source_pointer=f'/records/{target["source_id"]}/all_properties/response/propConceptGroup/propConcept/{i}') for i, v in enumerate(props) if v.get('propCategory') == 'NAMES']
                    if source == 'pubchem':
                        aliases = collections[source]['records'][str(target['source_id'])]['synonyms'].get('Synonym', [])
                        item['matching_aliases'] = [{'value': a, 'source_pointer': f'/records/{target["source_id"]}/synonyms/Synonym/{i}'} for i, a in enumerate(aliases) if 'linolenic' in a.lower()][:30]
                    candidates.append(item)
                    relation, recommendation, req, reason = PROPOSALS[(query, source)]
                    rows.append({'case_id': case_id, 'label_id': str(label_id), 'origin_path': origin['json_path'], 'query': query,
                                 'target': target['id'], 'method': 'saved_lookup_candidate', 'relation': relation,
                                 'recommendation': recommendation, 'requirements': req, 'rationale': reason})
            if not candidates:
                req, reason = NO_TARGET[query]
                rows.append({'case_id': case_id, 'label_id': str(label_id), 'origin_path': origin['json_path'], 'query': query,
                             'target': None, 'method': 'saved_no_candidate', 'relation': None,
                             'recommendation': 'no_target', 'requirements': req, 'rationale': reason})
            case = {'case_id': case_id, 'origin': origin, 'occurrence': occurrence,
                    'candidates': candidates, 'lookup_outcomes': q['source_status'], 'additional_proposals': []}
            if query == 'alpha-linolenic acid':
                case['additional_proposals'].append({'method': 'manual_evidence_led_category_proposal',
                                                     'target': category_target, 'evidence': hierarchy})
                rows.append({'case_id': case_id, 'label_id': str(label_id), 'origin_path': origin['json_path'], 'query': query,
                             'target': category_target['id'], 'method': 'manual_evidence_led_category_proposal',
                             'relation': 'member_of_category', 'recommendation': 'supported_for_review', 'requirements': 'ING-02 ING-09',
                             'rationale': 'Explicit ALA source designation plus saved MeSH alpha-linolenic descriptor and its broaderDescriptor link to Omega-3 support a classification proposal. This is a separate occurrence-to-category assertion, not an automatic rewriting of the vocabulary edge or an original lookup hit.'})
            cases.append(case)
    from collections import Counter
    for r in rows:
        r.update({'mapping_semantics_version': SEMANTICS, 'review_state': 'needs_review', 'A6': 'pending',
                  'assessment_author_role': 'assistant', 'evidence_case_pointer': f'/cases/{int(r["case_id"].split("-")[1])-1}',
                  'approval_applied': False})
    assert len(cases) == 20 and len(rows) == 28
    assert sum(len(c['candidates']) for c in cases) == 17
    assert sum(r['method'] == 'manual_evidence_led_category_proposal' for r in rows) == 2
    assert sum(r['target'] is None for r in rows) == 9
    assert all(r['review_state'] == 'needs_review' and not r['approval_applied'] for r in rows)
    bylabel = {c['origin']['dsld_id']: c for c in cases if c['origin']['query_key'] == 'probiotic blend'}
    assert bylabel['11613']['occurrence']['ingredientId'] == bylabel['32494']['occurrence']['ingredientId']
    assert {x['name'] for x in bylabel['11613']['occurrence']['nestedRows']} != {x['name'] for x in bylabel['32494']['occurrence']['nestedRows']}
    # The saved synonym, rather than query matching alone, must support the powder recommendations.
    powder = [c for c in cases if c['origin']['query_key'] == 'turmeric root powder']
    assert all(any(p.get('propName') == 'RxNorm Synonym' and p.get('propValue', '').lower() == 'turmeric root powder' for p in c['candidates'][0]['saved_name_properties']) for c in powder)
    report = {'version': VERSION, 'semantics_version': SEMANTICS,
              'selection_policy': 'Purposive 12-class, 20-occurrence pilot. Generally the two lowest label IDs per selected query, or the only occurrence. Probiotic Blend 11613 intentionally repeats the earlier pilot for contrast with 32494. Not random or exhaustive.',
              'summary': {'query_classes': len(SELECTION), 'occurrences': len(cases), 'saved_candidate_links': 17,
                          'manual_category_proposals': 2, 'no_target_occurrences': 9, 'review_rows': len(rows),
                          'recommendation_counts': dict(Counter(r['recommendation'] for r in rows)),
                          'accepted_mappings': 0, 'merged_entities': 0},
              'cases': cases, 'review_rows': rows}
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)
    payloads = {'review.json': (json.dumps(report, ensure_ascii=False, indent=2)+'\n').encode(), 'mapping_review.csv': buf.getvalue().encode()}
    script_hash = sha(Path(__file__).read_bytes())
    out = project / 'data/processed/identity' / (VERSION + '-' + sha(json.dumps(inputs, sort_keys=True).encode()+script_hash.encode())[:16])
    if snapshot(project / 'data/raw') != before:
        raise RuntimeError('Raw data changed')
    output_manifest = {'version': VERSION, 'script_sha256': script_hash, 'inputs': inputs,
                       'raw_file_count': len(before), 'raw_files_unchanged': True,
                       'files': {name: {'sha256': sha(data), 'bytes': len(data)} for name, data in payloads.items()}}
    payloads['manifest.json'] = (json.dumps(output_manifest, indent=2)+'\n').encode()
    if out.exists():
        for name, data in payloads.items():
            if (out/name).read_bytes() != data:
                raise ValueError('Refusing altered existing output: '+name)
    else:
        out.mkdir(parents=True)
        for name, data in payloads.items():
            (out/name).write_bytes(data)
    return out, report


if __name__ == '__main__':
    output, report = review(Path(__file__).resolve().parents[1])
    print(output)
    print(json.dumps(report['summary'], indent=2))
