"""Context-supported candidate discovery; prior identity decisions and KG stay frozen."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from decide_ingredient_mappings import ROOT, DSLD, TERMS
from preprocess_pilot import encode, key, sha, search_key
from expand_topic_navigation import write_immutable

BASE = 'data/processed/identity/ingredient-decisions-v1-1e02682e87ad7456218b'
SPEC = 'schemas/contextual_mapping_review_v1.json'
PARTS = {'root', 'leaf', 'seed', 'flower', 'fruit', 'bark', 'rhizome', 'stem', 'aerial'}
PREPS = {'extract', 'powder', 'oil'}
FORMS = {'hydrochloride', 'monohydrate', 'dihydrate', 'trihydrate', 'anhydrous'}
SCOPES = PARTS | PREPS | FORMS | {'whole'}
BLOCKED = re.compile(r'\b(?:not|without|free|blend|complex|mixture)\b|[&+]')


def normalized(text):
    text = search_key(text or '')
    for a, b in [('leaves', 'leaf'), ('roots', 'root'), ('hcl', 'hydrochloride')]:
        text = re.sub(r'\b' + a + r'\b', b, text)
    return text


def qualifiers(text):
    return set(re.findall(r'\b[a-z]+\b', normalized(text))) & SCOPES


def family(text):
    text = normalized(text)
    if BLOCKED.search(text):
        return None
    # Do not remove punctuation, numbers, brands, salts, standardization or strain names.
    text = re.sub(r'\b(?:' + '|'.join(sorted(SCOPES)) + r')\b', ' ', text)
    text = ' '.join(text.split())
    return text if re.search(r'[a-z]', text) else None


def context(occurrence):
    name = occurrence['original_name']
    attrs = occurrence['attributes']
    notes = attrs.get('notes') or ''
    scope = qualifiers(name)
    anchors = [{'field': 'original_name', 'text': name}]
    match = re.search(r'\bPlantPart:\s*(.*?)(?=\b(?:Genus|Species|Form):|$)', notes, re.I)
    if match and not BLOCKED.search(normalized(match.group(1))):
        scope |= qualifiers(match.group(1)) & (PARTS | {'whole'})
        anchors.append({'field': 'attributes.notes', 'start': match.start(1),
                        'end': match.end(1), 'text': match.group(1)})
    genus = re.search(r'\bGenus:\s*([A-Za-z-]+)', notes)
    species = re.search(r'\bSpecies:\s*([A-Za-z-]+)', notes)
    return dict(scope=sorted(scope), anchors=anchors,
                allergenic_declared=bool(re.search(r'\ballergenic\b', normalized(name))),
                genus=genus.group(1).casefold() if genus else None,
                species=species.group(1).casefold() if species else None,
                discovery_allowed=not BLOCKED.search(normalized(name + ' ' + notes)))


def supported_query(occurrence, ctx, query):
    return bool(ctx['discovery_allowed'] and family(occurrence['original_name'])
                and family(occurrence['original_name']) == family(query)
                and qualifiers(query) <= set(ctx['scope']))


def assess(ctx, target, source, prior):
    name = target.get('display_name') or ''
    wanted, actual = set(ctx['scope']), qualifiers(name)
    reasons = []
    if prior and prior['confidence'] == 'Low':
        return 3, 'Low', ['prior_exclusion_preserved']
    if 'allergenic' in normalized(name).split() and not ctx.get('allergenic_declared', False):
        return 3, 'Low', ['unsupported_allergenic_preparation']
    for group, label in [(PARTS, 'plant_part'), (PREPS, 'preparation'), (FORMS, 'chemical_form')]:
        a, b = wanted & group, actual & group
        if a and b and not (a & b):
            reasons.append(label + '_conflict')
    if ctx['genus'] and ctx['species']:
        m = re.search(r'\b' + re.escape(ctx['genus']) + r'\s+([a-z-]+)', normalized(name))
        if m and m.group(1) != ctx['species']:
            reasons.append('species_conflict')
    if reasons:
        return 3, 'Low', reasons
    if wanted - actual:
        reasons.append('target_omits_explicit_scope')
    if actual - wanted:
        reasons.append('target_adds_unconfirmed_scope')
    if not wanted:
        reasons.append('no_explicit_scope_for_preference')
    if source == 'rxnorm' and target['original_fields'].get('suppress') != 'N':
        reasons.append('inactive_or_unknown_target_status')
    if source == 'mesh':
        # No unverified MeSH active-status inference in this discovery layer.
        reasons.append('mesh_definition_and_status_review_required')
    if source == 'pubchem':
        reasons.append('specific_structure_requires_material_review')
    if not reasons:
        return 1, 'Medium', ['explicit_scope_aligned_preferred_for_review_only']
    return 2, 'Medium', reasons


def build(root=ROOT):
    root = Path(root)
    inputs = {}
    def read(path):
        b = (root / path).read_bytes(); inputs[path] = sha(b)
        return b
    def rows(path):
        return [json.loads(l) for l in read(path).splitlines()]
    for folder in [BASE, DSLD, TERMS]:
        manifest = json.loads(read(folder + '/manifest.json'))
        for name, digest in manifest['files'].items():
            assert sha(read(folder + '/' + name)) == (digest if isinstance(digest, str) else digest['sha256'])
    read(SPEC)
    occurrences = {o['id']: o for o in rows(DSLD + '/occurrences.jsonl')}
    prior = rows(BASE + '/terminology_decisions.jsonl')
    old = defaultdict(list)
    for d in prior:
        old[(d['origin_occurrence_id'], d['target_source'], d['target_record_id'])].append(d)
    no_candidates = rows(BASE + '/no_candidate_queries.jsonl')
    no_pairs = {(r['origin_occurrence_id'], r['source']) for r in no_candidates}
    proposals = []
    targets_by_source = {}
    for source in ['pubchem', 'rxnorm', 'mesh']:
        folder = TERMS + '/' + source
        queries = {q['id']: q for q in rows(folder + '/queries.jsonl')}
        targets = {r['id']: r for r in rows(folder + '/records.jsonl')}
        for index, target in enumerate(targets.values()):
            if source == 'mesh':
                target['display_name'] = next((v['value'] for v in target['original_fields']['labels'] if v.get('xml:lang', 'en') == 'en'), None)
                target['provenance'] = dict(file=folder+'/records.jsonl', pointer='/'+str(index), sha256=inputs[folder+'/records.jsonl'], rdf_statement_ids=target['rdf_statement_ids'])
        targets_by_source[source] = targets
        candidates = defaultdict(list)
        for c in rows(folder + '/candidates.jsonl'):
            candidates[c['query_id']].append(c)
        families = defaultdict(list)
        for q in queries.values():
            f = family(q['original_query'])
            if f and candidates[q['id']]:
                families[f].append(q)
        source_origins = {r['dsld_occurrence_id'] for r in rows(folder + '/query_origins.jsonl')}
        for oid in sorted(source_origins):
            o = occurrences[oid]; ctx = context(o)
            evidence_by_target = defaultdict(list)
            for q in families.get(family(o['original_name']), []):
                if not supported_query(o, ctx, q['original_query']):
                    continue
                for c in candidates[q['id']]:
                    tid = c['target_record_id']
                    # Existing pairs are retained in the unchanged base, not re-proposed.
                    if (oid, source, tid) in old:
                        continue
                    evidence_by_target[tid].append(dict(query_id=q['id'], query=q['original_query'],
                        query_provenance=q['provenance'], candidate_id=c['id'], candidate_provenance=c['provenance']))
            for tid, discovery in sorted(evidence_by_target.items()):
                target = targets[tid]
                rank, confidence, reasons = assess(ctx, target, source, None)
                proposals.append(dict(id=key('contextual_mapping_proposal', oid, source, tid, SPEC),
                    origin_occurrence_id=oid, original_name=o['original_name'], origin_role=o['role'],
                    source_attributes=o['attributes'], target_source=source, target_record_id=tid,
                    target_native_id=target['native_id'], target_name=target.get('display_name'),
                    context=ctx, dsld_evidence_ids=o['evidence_ids'], discovery=discovery,
                    target_provenance=target['provenance'], target_table=folder+'/records.jsonl',
                    review_priority=rank, confidence=confidence, reasons=reasons,
                    action='exclude_exact_match' if confidence == 'Low' else 'pending_scope_review',
                    proposed_relation=None, graph_applied=False, human_reviewed=False, clinical_approval=False,
                    original_query_had_no_candidate=(oid, source) in no_pairs))
    comparisons = []
    byorigin = defaultdict(list)
    for p in proposals:
        byorigin[(p['origin_occurrence_id'], p['target_source'])].append(p)
    for (oid, source), added in sorted(byorigin.items()):
        o = occurrences[oid]; ctx = context(o)
        targets = targets_by_source[source]
        existing = [d for d in prior if d['origin_occurrence_id']==oid and d['target_source']==source]
        ranked = []
        for d in existing:
            rank, _, reasons = assess(ctx, targets[d['target_record_id']], source, d)
            ranked.append(dict(target_native_id=d['target_native_id'], target_name=d['target_name'],
                prior_decision_id=d['id'], prior_confidence=d['confidence'], review_priority=rank,
                reasons=reasons, existing_decision_unchanged=True))
        ranked += [dict(target_native_id=p['target_native_id'], target_name=p['target_name'],
            proposal_id=p['id'], review_priority=p['review_priority'], reasons=p['reasons']) for p in added]
        preferred = sorted({r['target_native_id'] for r in ranked if r['review_priority']==1})
        comparisons.append(dict(origin_occurrence_id=oid, original_name=o['original_name'], source=source,
            candidates=ranked, preferred_for_review=preferred, ambiguous_preference=len(preferred)>1,
            selected_mapping=None, identity_approval=False))
    assert len({p['id'] for p in proposals}) == len(proposals)
    assert all(p['confidence'] != 'High' and not p['graph_applied'] and p['proposed_relation'] is None for p in proposals)
    assert all((p['origin_occurrence_id'], p['target_source'], p['target_record_id']) not in old for p in proposals)
    report = dict(version='contextual-mapping-review-v1', base_decisions=BASE,
        occurrences_examined=len(occurrences), existing_terminology_decisions_preserved=len(prior),
        new_candidate_pairs=len(proposals), affected_occurrences=len({p['origin_occurrence_id'] for p in proposals}),
        by_source=dict(Counter(p['target_source'] for p in proposals)),
        by_confidence=dict(Counter(p['confidence'] for p in proposals)),
        by_review_priority=dict(Counter(str(p['review_priority']) for p in proposals)),
        no_candidate_occurrence_source_pairs_with_new_proposals=len({(p['origin_occurrence_id'], p['target_source']) for p in proposals if p['original_query_had_no_candidate']}),
        ambiguous_preference_groups=sum(c['ambiguous_preference'] for c in comparisons),
        historical_no_candidate_rows_unchanged=len(no_candidates), new_accepted_mappings=0,
        graph_updated=False, limitations=json.loads(read(SPEC))['limitations'])
    return proposals, comparisons, report, inputs


def run(root=ROOT):
    root = Path(root)
    proposals, comparisons, report, inputs = build(root)
    signature = dict(inputs=inputs, code={p:sha((root/p).read_bytes()) for p in
        ['scripts/expand_contextual_mapping_candidates.py', 'tests/test_contextual_mapping_candidates.py']})
    files = {'new_candidates.jsonl': ''.join(encode(p)+'\n' for p in proposals).encode(),
             'candidate_comparisons.jsonl': ''.join(encode(c)+'\n' for c in comparisons).encode(),
             'review_report.json': (encode(report)+'\n').encode(),
             'input_manifest.json': (encode(signature)+'\n').encode()}
    for name, data in files.items():
        if name.endswith('.jsonl'):
            for line in data.splitlines():
                json.loads(line)
        else:
            json.loads(data)
    manifest = dict(spec=SPEC, base_decisions=BASE, files={p:sha(b) for p,b in files.items()})
    files['manifest.json']=(encode(manifest)+'\n').encode()
    out=root/'data/processed/identity'/('contextual-candidates-v1-'+sha(files['manifest.json'])[:20])
    write_immutable(out, files)
    for p,h in inputs.items():
        assert sha((root/p).read_bytes())==h
    print(out.relative_to(root));print(json.dumps(report,indent=2))
    return out, report

if __name__ == '__main__':
    run()
