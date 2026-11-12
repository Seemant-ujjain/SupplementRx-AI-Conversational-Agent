"""Audit stored DSLD quantities and serving references without correcting values."""
import csv
import io
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from review_dsld_name_groups import snapshot, sha

VERSION = 'dsld-quantity-audit-v1'

def numeric(value):
    return type(value) in (int,float) and math.isfinite(value)

def walk(rows, prefix='/ingredientRows'):
    for i,row in enumerate(rows or []):
        pointer=f'{prefix}/{i}'
        yield pointer,row
        yield from walk(row.get('nestedRows'),pointer+'/nestedRows')

def audit_label(label):
    findings=[]; counts=Counter(); units=Counter(); operators=Counter()
    def add(code,pointer,value,severity='review',context=None):
        findings.append({'label_id':str(label['id']), 'brand':label.get('brandName'),
                         'product':label.get('fullName'),'code':code,'severity':severity,
                         'pointer':pointer,'value':value,'context':context})
    servings=label.get('servingSizes') or []
    by_order=defaultdict(list)
    if not servings:add('missing_serving_definition','/servingSizes',servings,'error')
    for i,s in enumerate(servings):
        ptr=f'/servingSizes/{i}';order=s.get('order')
        if type(order) is not int or order<1:add('invalid_serving_order',ptr,s,'error')
        by_order[json.dumps(order)].append(s)
        if not isinstance(s.get('unit'),str) or not s['unit'].strip():add('missing_serving_unit',ptr,s,'error')
        for lo,hi in [('minQuantity','maxQuantity'),('minDailyServings','maxDailyServings')]:
            vals=[s.get(lo),s.get(hi)]
            if any(v is None for v in vals):add('incomplete_daily_serving_range' if lo=='minDailyServings' else 'incomplete_serving_size_range',ptr,s)
            elif not all(numeric(v) and v>0 for v in vals):add('invalid_serving_range',ptr,{lo:vals[0],hi:vals[1]},'error')
            elif vals[0]>vals[1]:add('reversed_serving_range',ptr,{lo:vals[0],hi:vals[1]},'error')
        # Limited heuristic: only explicit mL quantities in mL serving notes.
        # Notes can contain alternative units; no cross-unit comparison is made.
        if s.get('unit','').strip().lower()=='ml':
            amounts=[float(v) for v in re.findall(r'(?<![\w.])([0-9]+(?:\.[0-9]+)?)\s*ml\b',s.get('notes') or '',re.I)]
            if amounts and all(numeric(s.get(k)) for k in ['minQuantity','maxQuantity']):
                if all(not s['minQuantity']<=v<=s['maxQuantity'] for v in amounts):
                    add('ml_note_numeric_disagreement',ptr,s,context={'note_ml_values':amounts,'interpretation':'Candidate conflict; verify original label, do not auto-correct.'})
    for order,values in by_order.items():
        if len(values)>1:add('duplicate_serving_order','/servingSizes',values,'error')
    for ptr,row in walk(label.get('ingredientRows')):
        counts['ingredient_rows']+=1
        if '/nestedRows/' in ptr:counts['nested_ingredient_rows']+=1
        quantities=row.get('quantity') or []
        if not quantities:add('missing_ingredient_quantities',ptr,row)
        for i,q in enumerate(quantities):
            counts['quantity_entries']+=1; qp=f'{ptr}/quantity/{i}'
            unit=q.get('unit'); value=q.get('quantity'); op=q.get('operator')
            units[str(unit)]+=1;operators[str(op)]+=1
            context={'ingredient_name':row.get('name'),'ingredient_pointer':ptr}
            if unit=='NP':
                counts['np_entries']+=1
                if value==0:counts['np_zero_entries']+=1
                add('np_unit_unresolved',qp,q,context=context)
            elif not isinstance(unit,str) or not unit.strip():add('missing_quantity_unit',qp,q,'error',context)
            if not numeric(value):add('nonnumeric_or_nonfinite_amount',qp,q,'error',context)
            elif value<0:add('negative_amount',qp,q,'error',context)
            elif value==0 and unit!='NP':add('zero_amount_with_named_unit',qp,q,'info',context)
            if op not in ['=','<','<=','>','>=']:add('unsupported_operator',qp,q,'error',context)
            elif op!='=':add('inequality_amount',qp,q,'info',context)
            basis=q.get('servingSizeQuantity')
            if basis is None:add('missing_quantity_serving_basis',qp,q,context=context)
            elif not numeric(basis) or basis<=0:add('invalid_quantity_serving_basis',qp,q,'error',context)
            order=q.get('servingSizeOrder')
            if type(order) is not int or order<1:add('invalid_quantity_serving_order',qp,q,'error',context)
            targets=by_order.get(json.dumps(order),[])
            if len(targets)!=1:
                add('unresolved_serving_reference',qp,q,'error',context);continue
            s=targets[0]
            ctx={**context,'referenced_serving':s}
            if q.get('servingSizeUnit')!=s.get('unit'):
                add('serving_unit_text_mismatch',qp,q,context=ctx)
            elif numeric(basis) and all(numeric(s.get(k)) for k in ['minQuantity','maxQuantity']):
                if not s['minQuantity']<=basis<=s['maxQuantity']:
                    daily=[s.get('minDailyServings'),s.get('maxDailyServings')]
                    if all(numeric(v) for v in daily):
                        ctx['basis_within_computed_daily_range']=s['minQuantity']*daily[0]<=basis<=s['maxQuantity']*daily[1]
                    add('quantity_basis_outside_serving_range',qp,q,context=ctx)
    return findings,counts,units,operators

def audit(project):
    project=Path(project);raw=project/'data/raw';before=snapshot(raw)
    source=raw/'dsld/collection.json';data=source.read_bytes();collection=json.loads(data)
    labels=collection['labels'];ids=[str(l['id']) for l in labels]
    if len(ids)!=len(set(ids)) or collection['record_count']!=len(labels):raise ValueError('Invalid collection IDs/count')
    findings=[];counts=Counter();units=Counter();operators=Counter();sources={};serving_units=Counter()
    for label in labels:
        path=raw/'dsld/labels'/f"label_{label['id']}.json";b=path.read_bytes()
        if json.loads(b)!=label:raise ValueError('Collection and individual label differ')
        sources[str(label['id'])]={'file':str(path.relative_to(project)),'sha256':sha(b)}
        f,c,u,o=audit_label(label);findings.extend(f);counts.update(c);units.update(u);operators.update(o)
        serving_units.update(str(s.get('unit')) for s in label.get('servingSizes',[]))
    codes=sorted({f['code'] for f in findings})
    summary={'labels':len(labels),**dict(counts), 'serving_definitions':sum(serving_units.values()),
        'quantity_unit_counts':dict(units),'serving_unit_counts':dict(serving_units),'operator_counts':dict(operators),
        'findings_by_code':{c:{'occurrences':sum(f['code']==c for f in findings),
                             'labels':len({f['label_id'] for f in findings if f['code']==c})} for c in codes},
        'severity_counts':dict(Counter(f['severity'] for f in findings)),
        'labels_with_review_or_error':len({f['label_id'] for f in findings if f['severity']!='info'}),
        'out_of_serving_range_entries_within_computed_daily_range':sum(f['code']=='quantity_basis_outside_serving_range' and f['context'].get('basis_within_computed_daily_range',False) for f in findings),
        'missing_quantity_rows':sum(f['code']=='missing_ingredient_quantities' for f in findings),
        'nonnumeric_or_negative_amount_entries':sum(f['code'] in ['nonnumeric_or_nonfinite_amount','negative_amount'] for f in findings),
        'unresolved_serving_references':sum(f['code']=='unresolved_serving_reference' for f in findings),
        'serving_unit_text_mismatches':sum(f['code']=='serving_unit_text_mismatch' for f in findings),
        'records_corrected':0,'records_removed':0,'unit_conversions_applied':0}
    policy=['This audit examines stored values, not actual product doses or label accuracy.',
        'NP is an unresolved source unit code. Its zero values must not automatically be interpreted as zero ingredient content. Its official semantics have not been verified.',
        'Zero quantities with named units and inequality operators are informational; they are not automatically errors.',
        'Serving-reference checks preserve original units and ranges. Out-of-range quantities may describe a daily total or another basis; do not automatically reject or correct them.',
        'Serving-unit text mismatches may be aliases; matching text is not proof of correct units.',
        'Note checking is limited to explicit mL numbers in mL serving notes. No exhaustive free-text or image verification, daily-value validation, or nested blend-total arithmetic is performed.',
        'Mass, IU, enzyme activity, energy, volume and nutrient-equivalent units are not universally interchangeable. No conversions are applied.',
        'Every finding includes a JSON pointer into the original label. Counts are occurrences and distinct labels per code; categories overlap.']
    report={'summary':summary,'policy':policy,'findings':findings}
    lines=['# DSLD quantity and serving audit','','## Scope and limits','']+['- '+p for p in policy]+['','## Findings','','| Check | Occurrences | Labels |','|---|---:|---:|']
    for code,stat in summary['findings_by_code'].items():lines.append(f"| {code} | {stat['occurrences']} | {stat['labels']} |")
    lines+=['','## Complete summary','','```json',json.dumps(summary,indent=2),'```','','Detailed source values, context and JSON pointers are in audit.json. No values were corrected.','']
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=['label_id','brand','product','code','severity','pointer','value','context']);writer.writeheader()
    for f in findings:writer.writerow({**f,'value':json.dumps(f['value'],ensure_ascii=False),'context':json.dumps(f['context'],ensure_ascii=False)})
    payloads={'audit.json':(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode(),'audit.md':'\n'.join(lines).encode(),'findings.csv':buffer.getvalue().encode()}
    fingerprint=sha(json.dumps({'collection':sha(data),'script':sha(Path(__file__).read_bytes()),'sources':sources},sort_keys=True).encode())
    out=project/'data/processed/dsld'/(VERSION+'-'+fingerprint[:16])
    if snapshot(raw)!=before:raise RuntimeError('Raw files changed')
    manifest={'rules_version':VERSION,'script_sha256':sha(Path(__file__).read_bytes()),'collection_sha256':sha(data),'sources':sources,
        'raw_file_count':len(before),'raw_files_unchanged':True,'files':{n:{'sha256':sha(b),'bytes':len(b)} for n,b in payloads.items()}}
    payloads['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if out.exists():
        for n,b in payloads.items():
            if (out/n).read_bytes()!=b:raise ValueError('Refusing to overwrite edited output: '+n)
    else:
        out.mkdir(parents=True)
        for n,b in payloads.items():(out/n).write_bytes(b)
    return out,report

if __name__=='__main__':
    out,report=audit(Path(__file__).resolve().parents[1]);print(out);print(json.dumps(report['summary'],indent=2))
