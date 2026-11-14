"""Offline bounded preprocessing against contract 0.1.0. No semantic approvals."""
from __future__ import annotations
import hashlib
import io
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation, localcontext
from importlib.metadata import version
from pathlib import Path

CONTRACT = 'schemas/poc_preprocessing_contract_v0.1.json'
RUNS = {'pubchem':'20261028T035149634190Z','rxnorm':'20261028T060819025094Z','mesh':'20261028T062833838481Z'}
TOPICS = ['Magnesium','Vitamin D','Ashwagandha','Melatonin','Omega-3','Vitamin B12','Iron','Turmeric','Probiotics','Creatine']
MASS = {'g':('g',Decimal('1000')),'Gram(s)':('g',Decimal('1000')),'grams':('g',Decimal('1000')),
        'mg':('mg',Decimal(1)),'mcg':('mcg',Decimal('.001')),'ug':('mcg',Decimal('.001')),
        'µg':('mcg',Decimal('.001')),'μg':('mcg',Decimal('.001'))}

def sha(b): return hashlib.sha256(b).hexdigest()

def encode(x):
    """Deterministic JSON; original finite Decimal numbers stay JSON numbers."""
    if isinstance(x, Decimal):
        if not x.is_finite(): raise ValueError('Non-finite decimal')
        return str(x)
    if isinstance(x, dict): return '{'+','.join(json.dumps(k,ensure_ascii=False)+':'+encode(x[k]) for k in sorted(x))+'}'
    if isinstance(x, list): return '['+','.join(encode(v) for v in x)+']'
    return json.dumps(x,ensure_ascii=False,allow_nan=False,separators=(',',':'))

def load(text):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d: raise ValueError('Duplicate JSON key: '+k)
            d[k]=v
        return d
    return json.loads(text,parse_float=Decimal,object_pairs_hook=pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError('Invalid number: '+s)))

def key(kind,*parts):
    if not all(isinstance(p,str) for p in parts): raise TypeError('Identity components must be strings')
    return kind+':'+sha(json.dumps([kind,*parts],ensure_ascii=True,separators=(',',':')).encode())

def state(d,k):
    if k not in d:return 'absent'
    if d[k] is None:return 'null'
    if d[k] == '' or d[k] == [] or d[k] == {}:return 'empty'
    return 'present'

def states(d,fields=None): return {k:state(d,k) for k in (fields if fields is not None else d)}
def esc(s):return str(s).replace('~','~0').replace('/','~1')
def pointer(d,p):
    if not p:return d
    for t in p.strip('/').split('/'):
        t=t.replace('~1','/').replace('~0','~')
        d=d[int(t)] if isinstance(d,list) else d[t]
    return d

def dot_pointer(s):
    tokens=re.findall(r'[^.\[\]]+',s)
    return '/'+ '/'.join(esc(t) for t in tokens)

def search_key(s):return re.sub(r'\s+',' ',unicodedata.normalize('NFC',s).strip()).casefold()

def decimal_string(n):
    s=format(n,'f')
    return s.rstrip('0').rstrip('.') if '.' in s else s

def normalize_mass(q, conflict=False):
    """Return a comparison representation, never an equivalence decision."""
    val=q.get('quantity');unit=q.get('unit');op=q.get('operator')
    result={'normalized_value':None,'value_state':'present','outcome':'blocked','review_required':True,'reason_codes':[],
            'rule_id':'N-U02','parameters':{'operator':op,'basis_quantity':q.get('servingSizeQuantity'),
            'basis_unit':q.get('servingSizeUnit'),'serving_order':q.get('servingSizeOrder'),
            'original_numeric_token':str(val) if val is not None else None}}
    if conflict:
        result.update(value_state='conflicting',reason_codes=['source_numeric_text_conflict']);return result
    if unit=='NP':
        result.update(rule_id='N-Q02',value_state='explicit_unknown',reason_codes=['unsupported_source_amount']);return result
    if val is None:
        result.update(value_state='missing',reason_codes=['missing_amount']);return result
    if isinstance(val,bool) or not isinstance(val,(int,Decimal)):
        result.update(value_state='invalid',reason_codes=['unsupported_numeric_type']);return result
    if unit not in MASS:
        result['reason_codes']=['unsupported_unit'];return result
    if op not in ['=','<','<=','>','>=']:
        result['reason_codes']=['unsupported_or_missing_operator'];return result
    amount=Decimal(val)
    if not amount.is_finite() or amount<0:
        result.update(value_state='invalid',reason_codes=['invalid_amount']);return result
    normalized_unit,factor=MASS[unit]
    with localcontext() as ctx:
        ctx.prec=max(50,len(amount.as_tuple().digits)+len(factor.as_tuple().digits)+10)
        comparison=amount*factor
    result.update(normalized_value={'amount':decimal_string(comparison),'unit':'mg','operator':op,
                 'basis_quantity':q.get('servingSizeQuantity'),'basis_unit':q.get('servingSizeUnit'),
                 'serving_order':q.get('servingSizeOrder')},outcome='normalized',review_required=False)
    result['parameters'].update(normalized_source_unit=normalized_unit,conversion_factor=decimal_string(factor),conversion_target='mg')
    basis=q.get('servingSizeQuantity')
    if not isinstance(basis,(int,Decimal)) or isinstance(basis,bool) or basis<=0 or not q.get('servingSizeUnit'):
        result['reason_codes'].append('missing_or_invalid_basis')
    if amount==0:result['reason_codes'].append('zero_named_unit_needs_review')
    result['review_required']=bool(result['reason_codes'])
    return result


def reference_states(original,target=None,valid=True):
    if original is None or original=='':
        return dict(target_key=None,identifier_state='missing',target_availability='not_assessable',resolution_state='unresolved',content_status='not_assessed',target_record_id=None,target_snapshot_id=None,reason_codes=['missing_identifier'])
    if not valid:
        return dict(target_key=None,identifier_state='invalid',target_availability='not_assessable',resolution_state='unresolved',content_status='not_assessed',target_record_id=None,target_snapshot_id=None,reason_codes=['invalid_identifier'])
    return dict(identifier_state='usable',target_availability='collected' if target else 'not_collected',
                resolution_state='resolved' if target else 'unresolved',content_status='not_assessed',
                target_record_id=target[0] if target else None,target_snapshot_id=target[1] if target else None,
                reason_codes=[] if target else ['target_outside_selected_pilot'])

class Pilot:
    def __init__(self,root):
        self.root=Path(root);self.inputs={};self.data={};self.tables={};self.expected=Counter();self.selected={}
        self.contract=load(self.read(CONTRACT));self.tables={t:{} for t in self.contract['tables']}
        self.source_targets={};self.snap_data={};self.evidence_checks=0;self.field_support_checks=0
        self.protected=self.protected_hashes()
    def protected_hashes(self):
        files=[p for base in ['data/raw','data/processed'] for p in (self.root/base).rglob('*') if p.is_file() and p.name!='.DS_Store' and not p.is_relative_to(self.root/'data/processed/poc')]
        files += [p for p in [self.root/'read.md'] if p.exists()]
        return {str(p.relative_to(self.root)):sha(p.read_bytes()) for p in files}
    def read(self,path,expected=None):
        b=(self.root/path).read_bytes();h=sha(b)
        if expected is not None and h!=expected:raise ValueError('Input hash mismatch: '+path)
        self.inputs[path]={'sha256':h,'bytes':len(b)}
        return b
    def document(self,path,expected=None):
        b=self.read(path,expected)
        if path not in self.data:
            self.data[path]=[load(l) for l in b.decode().splitlines() if l.strip()] if path.endswith('.jsonl') else load(b)
        return self.data[path]
    def add(self,table,id,**values):
        row={'id':id,'contract_version':self.contract['version'],**values}
        if id in self.tables[table] and self.tables[table][id]!=row:raise ValueError('Conflicting replay key: '+table)
        self.tables[table][id]=row
        return id
    def artifact(self,path):
        if path not in self.inputs:self.read(path)
        m=self.inputs[path];id=key('artifact',path,m['sha256'])
        self.add('artifacts',id,relative_path=path,sha256=m['sha256'],byte_length=m['bytes'],media_type='application/x-ndjson' if path.endswith('.jsonl') else 'application/json')
        return id
    def source(self,src,typ,native,path,loc,payload,role,run=None,observed=None,imported=None,version_info=None):
        rid=key('record',src,typ,str(native));aid=self.artifact(path)
        self.add('source_records',rid,source_system=src,native_type=typ,native_id=str(native),source_role=role,original_identity={'value':native,'source_type':type(native).__name__})
        sid=key('snapshot',rid,'raw-bytes-v1','container_bound_record',self.inputs[path]['sha256'],encode(loc))
        self.add('snapshots',sid,record_id=rid,artifact_id=aid,locator=loc,representation_kind=typ,
                 fingerprint_profile='raw-bytes-v1',payload_scope='container_bound_record',payload_digest=self.inputs[path]['sha256'],attributes=payload,field_states=states(payload))
        self.snap_data[sid]=(path,loc)
        self.source_targets[(src,typ,str(native))]=(rid,sid)
        cid=key('capture',src,run or path,path,observed or '',imported or '')
        prev=self.tables['capture_events'].get(cid)
        snapshots=sorted(set((prev['snapshot_ids'] if prev else [])+[sid]))
        capture_version=dict(prev['source_version']) if prev else {}
        for name,value in (version_info or {}).items():
            if name in capture_version and capture_version[name]!=value:
                raise ValueError('Conflicting source version in one capture')
            capture_version[name]=value
        if prev:del self.tables['capture_events'][cid]
        self.add('capture_events',cid,run_id=run or path,artifact_id=aid,snapshot_ids=snapshots,
                 observed_at_original=observed,imported_at_original=imported,source_version=capture_version,
                 metadata={'archived_observation':True,'not_processing_time':True})
        return rid,sid
    def evidence(self,sid,path,role,original=None,kind='json_pointer',span=None):
        file,_=self.snap_data[sid];data=self.data[file]
        loc={'pointer':path};present='present'
        try:value=pointer(data,path)
        except (KeyError,IndexError):value=None;present='absent'
        if kind=='character_span':
            start,end=span
            if not isinstance(value,str) or not 0<=start<end<=len(value):raise ValueError('Invalid span')
            value=value[start:end];loc.update(start=start,end=end,coordinate_system='unicode_codepoints')
        if original is not None and value!=original:raise ValueError('Evidence mismatch')
        eid=key('evidence',sid,kind,encode(loc),role)
        self.add('evidence',eid,snapshot_id=sid,artifact_id=self.tables['snapshots'][sid]['artifact_id'],locator_kind=kind,locator=loc,support_role=role,original_value=value,original_presence=present)
        return eid
    def queue(self,table,owner,stage,reasons,evidence):
        if reasons:self.add('review_queue',key('issue',table,owner,stage,*sorted(reasons)),owner_table=table,owner_id=owner,stage=stage,reason_codes=sorted(set(reasons)),status='needs_review',evidence_ids=evidence)
    def transform(self,table,owner,field,original,presence,ev,rule,normalized,parameters=None,outcome=None,reasons=None,value_state='present',review=False):
        reasons=reasons or []
        id=key('transformation',table,owner,field,rule,self.contract['rule_versions']['normalization'])
        self.add('transformations',id,owner_table=table,owner_id=owner,destination_field=field,original_value=original,original_presence=presence,normalized_value=normalized,value_state=value_state,
                 outcome=outcome or ('unchanged' if normalized==original else 'normalized'),review_required=review,reason_codes=reasons,rule_id=rule,rule_version=self.contract['rule_versions']['normalization'],parameters=parameters or {},evidence_ids=ev)
        self.queue('transformations',id,'normalization',reasons,ev)
        return id
    def reference(self,sid,role,value,namespace,typ,ev,loc,valid=True):
        target=self.source_targets.get((namespace,typ,str(value)))
        s=reference_states(value,target,valid)
        if s['identifier_state']=='usable':s['target_key']={'source_system':namespace,'native_type':typ,'native_id':str(value),'availability_scope':'selected_pilot_output'}
        id=key('reference',sid,loc,role)
        self.add('source_references',id,source_snapshot_id=sid,role=role,original_reference=value,task_requirement=None,evidence_ids=[ev],**s)
        self.queue('source_references',id,'reference_resolution',s['reason_codes'],[ev])
        return id
    def occurrence(self,sid,path,row,parent=None,role='ingredient'):
        eid=self.evidence(sid,path,'ingredient_occurrence',row)
        oid=key('occurrence',sid,path,role)
        fields=['ingredientId','name','description','notes','prefix','percent','category','ingredientGroup','uniiCode','alternateNames','order']
        attrs={k:row[k] for k in fields if k in row}
        self.add('occurrences',oid,snapshot_id=sid,parent_id=parent,role=role,native_ingredient_id=row.get('ingredientId'),original_name=row.get('name'),attributes=attrs,field_states=states(row,fields),evidence_ids=[eid])
        self.expected['occurrences']+=1
        if row.get('name') is not None:
            name=row['name']
            if not isinstance(name,str):raise ValueError('Ingredient name must be text')
            self.transform('occurrences',oid,'display_name',name,'present',[eid],'N-T01',name.strip())
            self.transform('occurrences',oid,'search_name_key',name,'present',[eid],'N-T02',search_key(name))
        return oid,eid
    def assertion(self,sid,path,kind,fields,ev,occ=None,serv=None,subject=None,native=None,review=None,role='label_information'):
        aid=key('assertion',sid,path,kind,self.contract['rule_versions']['source_mapping'])
        self.add('assertions',aid,snapshot_id=sid,kind=kind,native_assertion_id=native,subject_snapshot_id=subject or sid,occurrence_id=occ,serving_id=serv,
                 original_fields=fields,field_states=states(fields),source_review=review or {},evidence_role=role,evidence_ids=ev)
        self.expected['assertions:'+kind]+=1
        return aid
    def dsld(self):
        manifest_path='data/processed/dsld/dsld-baseline-audit-v1-1487bf52f8e90a1f/manifest.json'
        m=self.document(manifest_path);cm=self.document('data/raw/dsld/collection_manifest.json')
        qm_path='data/processed/dsld/dsld-quantity-audit-v1-ae1a24aa4a66389a/manifest.json'
        qm=self.document(qm_path);qpath=qm_path.rsplit('/',1)[0]+'/audit.json'
        qa=self.document(qpath,qm['files']['audit.json']['sha256'])
        self.quantity_findings=qa['findings'];self.label_sids={};self.occ_by_path={}
        labels={}
        for lid in self.contract['pilot']['dsld_label_ids']:
            sm=m['sources'][str(lid)];d=self.document(sm['file'],sm['sha256'])
            if d['id']!=lid:raise ValueError('Label ID mismatch')
            labels[lid]=d
            attr={k:v for k,v in d.items() if k not in ['ingredientRows','otheringredients','statements','contacts','pdf','thumbnail']}
            rid,sid=self.source('dsld','label',lid,sm['file'],{'pointer':''},attr,'label_information',run='saved-dsld-collection',observed=cm.get('downloaded_at_utc'))
            self.label_sids[lid]=sid
        for lid,d in labels.items():
            sid=self.label_sids[lid];servings={}
            relevant=[f for f in self.quantity_findings if str(f['label_id'])==str(lid)]
            conflicts=[f for f in relevant if f['code']=='ml_note_numeric_disagreement']
            for i,s in enumerate(d['servingSizes']):
                path=f'/servingSizes/{i}';eid=self.evidence(sid,path,'serving_definition',s)
                id=key('serving',sid,path)
                self.add('servings',id,snapshot_id=sid,source_order=s.get('order'),attributes=s,field_states=states(s),evidence_ids=[eid])
                self.expected['servings']+=1
                if s.get('order') in servings:raise ValueError('Duplicate serving order')
                servings[s.get('order')]=id
                if conflicts:self.queue('servings',id,'source_conflict',['numeric_text_serving_conflict'],[eid])
            def walk(rows,base,parent=None,role='ingredient'):
                for i,row in enumerate(rows):
                    path=f'{base}/{i}';oid,eid=self.occurrence(sid,path,row,parent,role)
                    self.occ_by_path[(str(lid),path)]=oid
                    quantities=row.get('quantity') or []
                    if not quantities:
                        self.assertion(sid,path,'presence',{'original_name':row.get('name'),'role':role,'quantity_state':state(row,'quantity')},[eid],occ=oid)
                    for j,q in enumerate(quantities):
                        qp=path+f'/quantity/{j}';qe=self.evidence(sid,qp,'quantity',q)
                        serv=servings.get(q.get('servingSizeOrder'))
                        aid=self.assertion(sid,qp,'composition',{'quantity':q,'ingredient_role':role,'parent_occurrence_id':parent,'ingredient_name':row.get('name'),'notes':row.get('notes')},[eid,qe],occ=oid,serv=serv)
                        norm=normalize_mass(q,bool(conflicts))
                        self.transform('assertions',aid,'mass_comparison',q,'present',[qe],norm['rule_id'],norm['normalized_value'],parameters=norm['parameters'],outcome=norm['outcome'],reasons=norm['reason_codes'],value_state=norm['value_state'],review=norm['review_required'])
                        self.transform('assertions',aid,'explicit_basis',{'quantity':q.get('servingSizeQuantity'),'unit':q.get('servingSizeUnit'),'order':q.get('servingSizeOrder')},'present',[qe],'N-Q04',{'quantity':q.get('servingSizeQuantity'),'unit':q.get('servingSizeUnit'),'order':q.get('servingSizeOrder')})
                        self.transform('assertions',aid,'operator',q.get('operator'),state(q,'operator'),[qe],'N-Q03',q.get('operator'))
                        if not serv:self.queue('assertions',aid,'serving_resolution',['unresolved_serving_order'],[qe])
                        for f in relevant:
                            if f['pointer']==qp:self.queue('assertions',aid,'source_audit',[f['code']],[qe])
                    for j,f in enumerate(row.get('forms') or []):
                        fp=path+f'/forms/{j}';fo,fe=self.occurrence(sid,fp,f,oid,'form' if role=='ingredient' else 'other_form')
                        self.occ_by_path[(str(lid),fp)]=fo
                        self.assertion(sid,fp,'presence',{'original_name':f.get('name'),'role':'form','parent_occurrence_id':oid,'prefix':f.get('prefix'),'percent':f.get('percent')},[fe],occ=fo)
                    walk(row.get('nestedRows') or [],path+'/nestedRows',oid,role)
            walk(d['ingredientRows'],'/ingredientRows')
            walk((d.get('otheringredients') or {}).get('ingredients') or [],'/otheringredients/ingredients',role='other_ingredient')
            if (d.get('otheringredients') or {}).get('text'):
                ev=self.evidence(sid,'/otheringredients/text','other_ingredient_text')
                self.assertion(sid,'/otheringredients/text','label_statement',{'type':'other_ingredient_text','notes':d['otheringredients']['text']},[ev])
            for i,s in enumerate(d.get('statements') or []):
                typ=s.get('type','')
                if any(k in typ.lower() for k in ['direction','precaution','storage']):
                    path=f'/statements/{i}';ev=self.evidence(sid,path,'label_statement',s)
                    self.assertion(sid,path,'label_statement',s,[ev])
            for i,r in enumerate(d.get('labelRelationships') or []):
                path=f'/labelRelationships/{i}';ev=self.evidence(sid,path,'label_relationship',r)
                self.reference(sid,r['type'],r.get('labelId'),'dsld','label',ev,path,valid=type(r.get('labelId')) is int)
                self.expected['dsld_references']+=1
        self.selected['dsld_labels']=list(labels)
    def terminology(self):
        tm=self.document('data/processed/terminology/terminology-review-v1-34294732268f2352/manifest.json')
        sources={s:self.document(meta['file'],meta['sha256']) for s,meta in tm['inputs'].items()}
        selected={}
        for qk,q in sources['pubchem']['queries'].items():
            os=[o for o in q['occurrences'] if (o['dsld_id'],dot_pointer(o['json_path'])) in self.occ_by_path]
            if os:selected[qk]=os
        for s,c in sources.items():
            for qk in selected:
                if c['queries'][qk]!=sources['pubchem']['queries'][qk]:raise ValueError('Cross-source query inventory disagreement')
            for lid in self.label_sids:
                path=f'data/raw/dsld/labels/label_{lid}.json'
                if self.inputs[path]['sha256']!=c['dsld_provenance']['label_sha256'][str(lid)]:raise ValueError('Query label version mismatch')
        target_ids={s:set() for s in sources}
        for qk in selected:
            target_ids['pubchem'].update(str(v) for v in sources['pubchem']['search_results'][qk]['cids'])
            target_ids['rxnorm'].update(sources['rxnorm']['search_results'][qk]['rxcuis'])
            target_ids['mesh'].update(sources['mesh']['candidate_record_index'][qk])
        target_ids['mesh'].update(['http://id.nlm.nih.gov/mesh/D017962','http://id.nlm.nih.gov/mesh/D015525'])
        collection_sids={};targets={s:{} for s in sources}
        for s,c in sources.items():
            path=tm['inputs'][s]['file'];attrs={k:v for k,v in c.items() if k in ['source','started_at_utc','finished_at_utc','scope','version_start','version_end','search_policy','source_metadata_start','source_metadata_end']}
            _,sid=self.source(s,'collection_response',RUNS[s],path,{'pointer':''},attrs,'terminology_lookup',run=RUNS[s],observed=c.get('finished_at_utc'),version_info={k:attrs[k] for k in attrs if 'version' in k or 'metadata' in k})
            collection_sids[s]=sid
            if s=='mesh':continue
            for native in sorted(target_ids[s]):
                raw=c['records'][native];rp='/records/'+esc(native)
                if s=='pubchem':
                    if str(raw['cid'])!=native or str(raw['properties']['CID'])!=native:raise ValueError('CID inconsistency')
                    attrs=raw['properties'];role='ChemicalCompound';typ='compound'
                else:
                    attrs=raw['properties']['response']['properties'];role='TerminologyConcept';typ='rxnorm_concept'
                    if str(raw['rxcui'])!=native or str(attrs['rxcui'])!=native:raise ValueError('RxCUI inconsistency')
                rid,ts=self.source(s,typ,native,path,{'pointer':rp},attrs,role,run=RUNS[s],observed=c.get('finished_at_utc'))
                targets[s][native]=(rid,ts)
                props=[]
                if s=='pubchem':
                    props.extend((k,v,rp+'/properties/'+esc(k)) for k,v in raw['properties'].items())
                    props.extend(('synonym',v,rp+f'/synonyms/Synonym/{i}') for i,v in enumerate(raw['synonyms'].get('Synonym',[])))
                else:
                    props.extend((k,v,rp+'/properties/response/properties/'+esc(k)) for k,v in attrs.items())
                    for i,v in enumerate(raw['all_properties']['response'].get('propConceptGroup',{}).get('propConcept',[])):
                        if v['propCategory'] in ['NAMES','SOURCES'] or (v['propCategory']=='CODES' and v['propName'] in ['UNII_CODE','DRUGBANK','SNOMEDCT']):
                            props.append((v['propName'],v,rp+f'/all_properties/response/propConceptGroup/propConcept/{i}'))
                for name,value,pp in props:
                    e=self.evidence(ts,pp,'terminology_property',value)
                    self.add('term_values',key('term_value',ts,pp),snapshot_id=ts,property_name=name,typed_value={'value':value,'source_json_type':type(value).__name__},evidence_ids=[e])
        # MeSH: project the complete saved subgraphs for selected candidate records,
        # including described concept/term subjects; object-only targets remain references.
        c=sources['mesh'];path=tm['inputs']['mesh']['file'];bindings=[]
        for bi,batch in enumerate(c['record_subgraph_responses']):
            if not batch['complete']:raise ValueError('Truncated MeSH source batch')
            for pi,page in enumerate(batch['pages']):
                if page['status']!='ok':raise ValueError('Failed MeSH batch')
                for i,b in enumerate(page['response'].get('results',{}).get('bindings',[])):
                    if b['record']['value'] in target_ids['mesh']:
                        bindings.append((f'/record_subgraph_responses/{bi}/pages/{pi}/response/results/bindings/{i}',b))
        bysubject=defaultdict(list)
        for bp,b in bindings:bysubject[b['subject']['value']].append((bp,b))
        for uri,items in sorted(bysubject.items()):
            attrs={'uri':uri,'properties':[{'predicate':b['predicate']['value'],'object':b['object']} for _,b in items]}
            rid,ts=self.source('mesh','rdf_subject',uri,path,{'rdf_subject':uri,'container_pointer':'/record_subgraph_responses'},attrs,'TerminologyConcept',run=RUNS['mesh'],observed=c.get('finished_at_utc'))
            targets['mesh'][uri]=(rid,ts)
        if not target_ids['mesh']<=set(targets['mesh']):raise ValueError('Missing candidate subject description')
        for bp,b in bindings:
            uri=b['subject']['value'];rid,ts=targets['mesh'][uri];pred=b['predicate']['value'];obj=b['object'];ev=self.evidence(ts,bp,'rdf_statement',b,kind='rdf_statement')
            target=targets['mesh'].get(obj['value']) if obj['type']=='uri' else None
            ref=None
            if obj['type']=='uri':ref=self.reference(ts,pred,obj['value'],'mesh','rdf_subject',ev,bp)
            # D-11 set representation within the same source snapshot, retain every provenance binding.
            vid=key('rdf_statement',ts,uri,pred,encode(obj))
            old=self.tables['vocabulary_statements'].get(vid);evs=sorted(set((old['evidence_ids'] if old else [])+[ev]))
            if old:del self.tables['vocabulary_statements'][vid]
            self.add('vocabulary_statements',vid,snapshot_id=ts,subject_uri=uri,predicate_uri=pred,typed_object=obj,graph_scope=None,
                     target_record_id=target[0] if target else None,reference_id=ref,evidence_ids=evs)
            self.expected['mesh_binding_occurrences']+=1
        for s,c in sources.items():
            cs=collection_sids[s]
            for qk,os in sorted(selected.items()):
                q=c['queries'][qk];result=c['search_results'][qk];rp='/search_results/'+esc(qk)
                ev=self.evidence(cs,rp,'lookup_result',result);qev=self.evidence(cs,'/queries/'+esc(qk),'query_provenance',q)
                ids=([str(v) for v in result['cids']] if s=='pubchem' else result['rxcuis'] if s=='rxnorm' else c['candidate_record_index'][qk])
                lookup_evidence=[ev,qev]
                if s=='mesh':
                    lookup_evidence.append(self.evidence(cs,'/candidate_record_index/'+esc(qk),'candidate_record_index',ids))
                    resolved=set()
                    for bi,batch in enumerate(c['term_resolution_responses']):
                        if not batch['complete']:raise ValueError('Incomplete MeSH resolution batch')
                        for pi,page in enumerate(batch['pages']):
                            if page['status']!='ok':raise ValueError('Failed MeSH term resolution')
                            for i,b in enumerate(page['response'].get('results',{}).get('bindings',[])):
                                if b['term']['value'] in result['term_uris']:
                                    bp=f'/term_resolution_responses/{bi}/pages/{pi}/response/results/bindings/{i}'
                                    lookup_evidence.append(self.evidence(cs,bp,'term_concept_record_resolution',b))
                                    resolved.add(b['record']['value'])
                    if resolved!=set(ids):raise ValueError('MeSH term/concept/record resolution disagrees with candidate index')
                outcome='candidates_returned' if ids else 'no_candidate'
                if result['status'] not in ['ok','matched','not_found']:raise ValueError('Unsupported source lookup status')
                if not ids and result['status']!='not_found':raise ValueError('Cannot infer no-result from empty array')
                lid=key('lookup',cs,qk)
                self.add('lookups',lid,snapshot_id=cs,source_system=s,query_key=qk,query=q['query'],variants=q['variants'],method=result.get('match_method','saved_name_lookup'),
                         source_status=result['status'],outcome=outcome,candidate_target_keys=[{'source':s,'native_id':x} for x in ids],evidence_ids=lookup_evidence)
                if not ids:self.queue('lookups',lid,'identity',['no_candidate'],[ev,qev])
                self.expected['lookups']+=1
                for o in os:
                    op=dot_pointer(o['json_path']);oid=self.occ_by_path[(o['dsld_id'],op)]
                    occurrence=self.tables['occurrences'][oid]
                    if str(occurrence['native_ingredient_id'])!=str(o['ingredient_id']) or occurrence['original_name']!=o['name']:raise ValueError('Occurrence provenance mismatch')
                    self.add('lookup_origins',key('lookup_origin',lid,oid),lookup_id=lid,occurrence_id=oid,evidence_ids=[qev,*occurrence['evidence_ids']])
                    self.expected['lookup_origins']+=1
                    for native in ids:
                        rid,ts=targets[s][native];mid=key('mapping',lid,oid,rid,'candidate_unspecified')
                        tevs=[e['id'] for e in self.tables['evidence'].values() if e['snapshot_id']==ts]
                        if not tevs:raise ValueError('Mapping target has no evidence')
                        mes=[*lookup_evidence,*occurrence['evidence_ids'],tevs[0]]
                        self.add('mapping_assertions',mid,origin_occurrence_id=oid,target_record_id=rid,target_snapshot_id=ts,lookup_id=lid,relation='candidate_unspecified',origin_role=occurrence['role'],origin_scope={'original_name':o['name'],'unresolved':True},target_scope={'source':s,'native_id':native,'unresolved':True},review_state='needs_review',rule_versions=self.contract['rule_versions'],evidence_ids=mes)
                        self.queue('mapping_assertions',mid,'identity',['scope_review_required']+(['ambiguous_candidates'] if len(ids)>1 else []),mes)
                        self.expected['mapping_assertions']+=1
        self.selected['terminology']={'query_keys':sorted(selected),'candidate_ids':{s:sorted(v) for s,v in target_ids.items()},'described_mesh_subjects':sorted(bysubject)}

    def imported(self):
        for src,folder in [('natmedpro','natmed-baseline-audit-v1-b548c344b8c0a9b7'),('reddit','reddit-baseline-audit-v1-058aea355a5bb848')]:
            m=self.document(f'data/processed/{src}/{folder}/manifest.json')
            path=f'data/raw/{src}/records.jsonl';rows=self.document(path,m['inputs'][path]);cm=self.document(f'data/raw/{src}/collection_manifest.json',m['inputs'][f'data/raw/{src}/collection_manifest.json'])
            if src=='natmedpro':
                cp='data/raw/natmedpro/upstream_derived/pending_clinical/clinical_claims.jsonl';claims=self.document(cp,m['inputs'][cp]);selected_claims=[(i,r) for i,r in enumerate(claims) if r['id'] in self.contract['pilot']['natmed_claim_ids']]
                if len(selected_claims)!=len(self.contract['pilot']['natmed_claim_ids']):raise ValueError('Missing claim')
                selected_ids={r['source']['record_id'] for _,r in selected_claims}
            else:selected_ids=set(self.contract['pilot']['reddit_ids'])
            picked=[(i,r) for i,r in enumerate(rows) if r['id'] in selected_ids]
            if len(picked)!=len(selected_ids):raise ValueError('Missing imported record')
            sids={}
            for i,r in picked:
                if sha(r['text'].encode())!=r['content_hash']:raise ValueError('Imported text hash mismatch')
                if src=='reddit':
                    native=r['native_id'];typ=r['record_type'];role=r['evidence_role']
                    if native!=r['id'].removeprefix('reddit:') or not native.startswith('t1_' if typ=='comment' else 't3_'):raise ValueError('Reddit ID/type mismatch')
                else:native=r['id'];typ='monograph';role=r['evidence_role']
                _,sid=self.source(src,typ,native,path,{'pointer':f'/{i}','jsonl_line':i+1},r,role,run=cm['source_commit'],observed=r.get('collected_at'),imported=cm.get('imported_at_utc'),version_info={'source_commit':cm['source_commit'],'schema_version':r.get('schema_version')})
                sids[r['id']]=sid
            for i,r in picked:
                sid=sids[r['id']]
                for j,t in enumerate(r.get('supplements',[])):
                    name=t['supplement'] if isinstance(t,dict) else t
                    if name not in TOPICS:raise ValueError('Unknown topic: '+name)
                    p=f'/{i}/supplements/{j}';ev=self.evidence(sid,p,'topic_context',t)
                    self.add('topic_associations',key('topic_association',sid,p),snapshot_id=sid,topic_key=key('topic',name),original_topic=name,matched_terms=t.get('matched_terms',[]) if isinstance(t,dict) else [],mention_scope=r.get('mention_scope'),scope_level='record',evidence_ids=[ev])
                    self.expected['topic_associations']+=1
                if src=='reddit':
                    for field,relation in [('parent_id','REPLY_TO'),('thread_id','IN_THREAD')]:
                        value=r.get(field);typ='comment' if isinstance(value,str) and value.startswith('t1_') else 'post'
                        valid=isinstance(value,str) and bool(re.fullmatch(r't[13]_[a-z0-9]+',value)) and (field!='thread_id' or value.startswith('t3_'))
                        ev=self.evidence(sid,f'/{i}/{field}',relation)
                        self.reference(sid,relation,value,'reddit',typ,ev,f'/{i}/{field}',valid=valid)
                        self.expected['reddit_references']+=1
                else:
                    # Title is scalar: source-bound subject occurrence gets scalar evidence, not fabricated row evidence.
                    ev=self.evidence(sid,f'/{i}/title','monograph_subject',r['title']);oid=key('occurrence',sid,f'/{i}/title','monograph_subject')
                    self.add('occurrences',oid,snapshot_id=sid,parent_id=None,role='monograph_subject',native_ingredient_id=None,original_name=r['title'],attributes={'name':r['title']},field_states={'name':'present','ingredientId':'absent'},evidence_ids=[ev])
                    self.expected['occurrences']+=1
                    for j,doc in enumerate(r.get('reference_documents',[])):
                        dp=f'/{i}/reference_documents/{j}'
                        if sha(doc['text'].encode())!=doc['content_hash']:raise ValueError('Bibliography text hash mismatch')
                        self.source(src,'reference_document',r['id']+':'+str(j),path,{'pointer':dp,'jsonl_line':i+1},doc,'bibliography',run=cm['source_commit'],observed=doc.get('captured_at'),imported=cm.get('imported_at_utc'))
            if src=='natmedpro':
                from jsonschema import Draft202012Validator,FormatChecker
                sp='data/raw/natmedpro/upstream_derived/pending_clinical/clinical_claim.schema.json';schema=self.document(sp,m['inputs'][sp]);validator=Draft202012Validator(schema,format_checker=FormatChecker())
                byid={r['id']:(i,r) for i,r in picked}
                for ci,c in selected_claims:
                    validator.validate(c)
                    ri,r=byid[c['source']['record_id']];ss=sids[r['id']];source=c['source'];sec=r['sections'][source['section_index']]
                    if source['content_hash']!=r['content_hash'] or source['url']!=r['source_url'] or source['section_heading']!=sec['heading'] or c['claim_text']!=source['excerpt'] or c['ingredient']['name']!=r['title']:raise ValueError('Claim source binding mismatch')
                    _,cs=self.source(src,'clinical_annotation',c['id'],cp,{'pointer':f'/{ci}','jsonl_line':ci+1},c,'pending_clinical_annotation',run=cm['source_commit'],imported=cm.get('imported_at_utc'))
                    ev=self.evidence(cs,f'/{ci}','clinical_annotation',c)
                    textpath=f'/{ri}/sections/{source["section_index"]}/text'
                    support=[ev,self.evidence(ss,textpath,'claim_excerpt',source['excerpt'],'character_span',(source['start'],source['end']))]
                    for field,anchor in c['field_support'].items():
                        val=c
                        for part in field.split('.'):val=val[part]
                        observed=sec['text'][anchor['start']:anchor['end']]
                        if isinstance(val,(int,Decimal)):
                            if Decimal(observed.strip())!=Decimal(val):raise ValueError('Field numeric anchor mismatch')
                        elif val!=observed:raise ValueError('Field support mismatch')
                        support.append(self.evidence(ss,textpath,field,observed,'character_span',(anchor['start'],anchor['end'])))
                        self.field_support_checks+=1
                    oid=key('occurrence',ss,f'/{ri}/title','monograph_subject')
                    aid=self.assertion(cs,f'/{ci}','clinical',c,support,occ=oid,subject=ss,native=c['id'],review=c['review'],role='clinical_reference')
                    self.queue('assertions',aid,'clinical_review',['source_review_pending','claim_citation_extraction_deferred'],support)
                self.selected['natmed_claims']=[c['id'] for _,c in selected_claims]
                self.selected['natmed_monographs']=sorted(selected_ids)
            else:self.selected['reddit_records']=sorted(selected_ids)
    def build(self):
        self.dsld();self.terminology();self.imported()
        validate_tables(self.tables,self.contract)
        # Verify every exported evidence value against the immutable source and coordinate system.
        for e in self.tables['evidence'].values():
            path=self.tables['artifacts'][e['artifact_id']]['relative_path'];loc=e['locator']
            try:actual=pointer(self.data[path],loc['pointer']);present='present'
            except (KeyError,IndexError):actual=None;present='absent'
            if e['locator_kind']=='character_span':actual=actual[loc['start']:loc['end']]
            if actual!=e['original_value'] or present!=e['original_presence']:raise ValueError('Exported evidence no longer matches source')
            self.evidence_checks+=1
        for name in ['occurrences','servings','lookups','lookup_origins','mapping_assertions','topic_associations']:
            if len(self.tables[name])!=self.expected[name]:raise ValueError('Multiplicity reconciliation: '+name)
        for kind in ['composition','presence','clinical','label_statement']:
            if sum(r['kind']==kind for r in self.tables['assertions'].values())!=self.expected['assertions:'+kind]:raise ValueError('Assertion reconciliation')
        # Independent inventory of source quantity and form paths for selected labels.
        source_rows=source_forms=source_quantities=source_other=0
        def count(rows):
            nonlocal source_rows,source_forms,source_quantities
            for r in rows:
                source_rows+=1;source_forms+=len(r.get('forms') or []);source_quantities+=len(r.get('quantity') or [])
                count(r.get('nestedRows') or [])
        for lid in self.label_sids:
            d=self.data[f'data/raw/dsld/labels/label_{lid}.json'];count(d['ingredientRows'])
            other=(d.get('otheringredients') or {}).get('ingredients') or []
            source_other+=sum(1+len(r.get('forms') or []) for r in other)
        dsld_occs=[o for o in self.tables['occurrences'].values() if o['snapshot_id'] in self.label_sids.values()]
        if len(dsld_occs)!=source_rows+source_forms+source_other:raise ValueError('Source occurrence inventory mismatch')
        if self.expected['assertions:composition']!=source_quantities:raise ValueError('Source quantity inventory mismatch')
        self.inventory={'dsld_recursive_rows':source_rows,'dsld_forms':source_forms,'dsld_other_occurrences':source_other,'dsld_quantity_entries':source_quantities}
        # Regression checks on actual outputs, distinct from synthetic fixtures.
        amounts={}
        for t in self.tables['transformations'].values():
            if t['destination_field']=='mass_comparison':
                a=self.tables['assertions'][t['owner_id']]
                for lid,sid in self.label_sids.items():
                    if a['snapshot_id']==sid and a['original_fields']['ingredient_name']=='Creatine':amounts[lid]=t
        if any(amounts[l]['normalized_value']['amount']!='1500' for l in [25731,43261]):raise ValueError('BPI comparison mismatch')
        if not any(t['value_state']=='conflicting' and t['normalized_value'] is None for t in self.tables['transformations'].values()):raise ValueError('Serving conflict lost')
        if self.protected_hashes()!=self.protected:raise ValueError('Protected files changed')
        return self


def validate_tables(tables,contract):
    """Fail closed on structural, FK, evidence-role and pilot semantic violations."""
    def require(ok,message):
        if not ok:raise ValueError(message)
    def matches(v,t):
        if t.endswith('?'):return v is None or matches(v,t[:-1])
        if t.endswith('[]'):return isinstance(v,list) and all(matches(x,t[:-2]) for x in v)
        return {'string':lambda:isinstance(v,str),'integer':lambda:type(v) is int,'boolean':lambda:type(v) is bool,
                'object':lambda:isinstance(v,dict),'json':lambda:True}[t]()
    require(set(tables)==set(contract['tables']),'Table inventory')
    for name,rows in tables.items():
        spec=contract['tables'][name]
        for id,r in rows.items():
            require(set(r)==set(spec['fields']),'Fields: '+name)
            require(id==r['id'] and r['contract_version']==contract['version'],'Row identity/version')
            for f,t in spec['fields'].items():require(matches(r[f],t),'Type: '+name+'.'+f)
            encode(r) # finite JSON numeric check
            for f,target in spec['foreign_keys'].items():
                vals=r[f] if isinstance(r[f],list) else [r[f]]
                for value in vals:
                    if value is not None:require(value in tables[target],'Broken FK: '+name+'.'+f)
            if 'evidence_ids' in r:require(bool(r['evidence_ids']),'Empty evidence: '+name)
            if 'owner_table' in r:require(r['owner_table'] in tables and r['owner_id'] in tables[r['owner_table']],'Broken polymorphic owner')
    for t in ['canonical_identities','comparison_groups','review_events','passages']:require(not tables[t],'Forbidden pilot output: '+t)
    def snapshot_record(s):return tables['source_records'][tables['snapshots'][s]['record_id']]
    for s in tables['snapshots'].values():
        require(s['payload_scope']=='container_bound_record' and s['fingerprint_profile']=='raw-bytes-v1','Snapshot profile')
        require(s['payload_digest']==tables['artifacts'][s['artifact_id']]['sha256'],'Snapshot digest')
    for e in tables['evidence'].values():
        require(e['artifact_id']==tables['snapshots'][e['snapshot_id']]['artifact_id'],'Evidence artifact binding')
        require(e['locator_kind'] in ['json_pointer','character_span','rdf_statement'],'Locator kind')
        require(isinstance(e['locator'].get('pointer'),str),'Evidence pointer')
        if e['locator_kind']=='character_span':
            require(type(e['locator'].get('start')) is int and type(e['locator'].get('end')) is int and 0<=e['locator']['start']<e['locator']['end'],'Span coordinates')
    for o in tables['occurrences'].values():
        if o['parent_id']:require(tables['occurrences'][o['parent_id']]['snapshot_id']==o['snapshot_id'],'Cross-label occurrence parent')
        require(o['role'] in ['ingredient','form','other_ingredient','other_form','monograph_subject'],'Occurrence role')
    for a in tables['assertions'].values():
        require(a['kind'] in ['composition','presence','label_statement','clinical'],'Assertion kind')
        if a['kind']=='clinical':
            require(snapshot_record(a['subject_snapshot_id'])['source_system']=='natmedpro','Non-NatMed clinical claim')
            require(a['source_review'].get('state')=='pending' and a['original_fields']['review']==a['source_review'],'Clinical approval or altered review')
            require(a['evidence_role']=='clinical_reference','Clinical role')
            for field in ['ingredient','population','indication','dose','interaction','source','claim_type','field_support']:
                require(field in a['original_fields'],'Missing clinical context')
            require(set(a['original_fields']['dose'])>={'value','unit','route','duration','minimum','maximum','qualifier','regimen','frequency','text'},'Dose context fields')
            require(set(a['original_fields']['interaction'])>={'partner','rating','severity','occurrence'},'Interaction context fields')
            require(snapshot_record(a['subject_snapshot_id'])['native_id']==a['original_fields']['source']['record_id'],'Wrong monograph source binding')
        else:
            require(a['subject_snapshot_id']==a['snapshot_id'],'Wrong label subject')
            if a['kind']=='composition':
                require(a['occurrence_id'] is not None,'Quantity without occurrence')
                require(tables['occurrences'][a['occurrence_id']]['role'] not in ['form','other_form'],'Parent amount copied to form')
                q=a['original_fields'].get('quantity');require(isinstance(q,dict) and {'quantity','unit','operator'}<=set(q),'Incomplete quantity projection')
        if a['occurrence_id']:require(tables['occurrences'][a['occurrence_id']]['snapshot_id']==a['subject_snapshot_id'],'Assertion occurrence scope')
        if a['serving_id']:require(tables['servings'][a['serving_id']]['snapshot_id']==a['snapshot_id'],'Cross-label serving')
    for m in tables['mapping_assertions'].values():
        require(m['relation']=='candidate_unspecified' and m['review_state'] in ['unreviewed','needs_review'],'Unauthorized mapping approval')
        require(tables['snapshots'][m['target_snapshot_id']]['record_id']==m['target_record_id'],'Mapping target mismatch')
        require(any(e['snapshot_id']==m['target_snapshot_id'] for e in (tables['evidence'][id] for id in m['evidence_ids'])),'No target evidence')
    for r in tables['source_references'].values():
        for field in ['identifier_state','target_availability','resolution_state','content_status']:
            require(r[field] in contract['enums'][field],'Reference enum')
        if r['identifier_state']!='usable':
            require(r['target_key'] is None and r['target_record_id'] is None and r['target_snapshot_id'] is None and r['target_availability']=='not_assessable' and r['resolution_state']!='resolved','Fabricated missing target')
        else:
            require(r['target_key'] is not None,'Usable key missing')
            if r['target_availability']=='not_collected':require(r['target_record_id'] is None and r['target_snapshot_id'] is None and r['resolution_state']=='unresolved','Uncollected target fabricated')
        if r['resolution_state']=='resolved':
            require(r['target_snapshot_id'] is not None and r['target_availability']=='collected','Resolved absent target')
            rec=snapshot_record(r['target_snapshot_id']);tk=r['target_key']
            require(tables['snapshots'][r['target_snapshot_id']]['record_id']==r['target_record_id'],'Reference target binding')
            require((rec['source_system'],rec['native_type'],rec['native_id'])==(tk['source_system'],tk['native_type'],tk['native_id']),'Reference namespace/type mismatch')
    for t in tables['transformations'].values():
        require(t['outcome'] in contract['enums']['normalization_outcome'],'Normalization outcome')
        require(t['rule_id'] in ['N-T01','N-T02','N-U02','N-Q02','N-Q03','N-Q04'],'Outside normalization allowlist')
        if t['outcome']=='blocked':require(t['normalized_value'] is None and t['review_required'],'Blocked value fabricated')
        if t['destination_field']=='mass_comparison':
            original=t['original_value'];nv=t['normalized_value']
            require(isinstance(original,dict),'Quantity original must be object')
            if original.get('unit')=='NP':require(nv is None and t['value_state']=='explicit_unknown','NP coerced to zero')
            if nv is not None:
                require(nv['operator']==original.get('operator') and nv['basis_quantity']==original.get('servingSizeQuantity') and nv['basis_unit']==original.get('servingSizeUnit'),'Operator/basis changed')
                require(isinstance(nv['amount'],str),'Derived quantity must be decimal string')
                require(Decimal(nv['amount']).is_finite(),'Invalid normalized decimal')
    for topic in tables['topic_associations'].values():
        require(topic['original_topic'] in TOPICS and topic['topic_key']==key('topic',topic['original_topic']),'Topic registry')
        require(topic['scope_level']=='record','Invented per-topic direct mention')
        snap=tables['snapshots'][topic['snapshot_id']]
        if snapshot_record(topic['snapshot_id'])['source_system']=='reddit':
            require(topic['mention_scope']==snap['attributes'].get('mention_scope'),'Mention scope changed')
    # All captured source RDF statement term details remain typed rather than label-deduplicated.
    for v in tables['vocabulary_statements'].values():
        require(v['typed_object'].get('type') in ['uri','literal','typed-literal','bnode'] and isinstance(v['typed_object'].get('value'),str),'Invalid RDF object')


def run_fixtures(root):
    import unittest
    suite=unittest.defaultTestLoader.discover(str(Path(root)/'tests'),pattern='test_preprocess_pilot.py')
    output=io.StringIO();result=unittest.TextTestRunner(stream=output,verbosity=1).run(suite)
    if not result.wasSuccessful():raise ValueError('Pilot fixtures failed:\n'+output.getvalue())
    return {'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}


def run(root,write=True):
    root=Path(root)
    fixtures=run_fixtures(root) # fail before transformations/output writing
    p=Pilot(root).build()
    code_files=['scripts/preprocess_pilot.py','tests/test_preprocess_pilot.py']
    config={'pilot':p.contract['pilot'],'topics':TOPICS,'availability_scope':'selected_pilot_output','implementation_version':'pilot-v1'}
    signature={'contract_sha256':sha((root/CONTRACT).read_bytes()),'inputs':p.inputs,'selection':p.selected,
               'code_hashes':{f:sha((root/f).read_bytes()) for f in code_files},'configuration_sha256':sha(encode(config).encode()),
               'rule_versions':p.contract['rule_versions'],'dependencies':{'python':sys.version.split()[0],'unicode':unicodedata.unidata_version,'jsonschema':version('jsonschema')}}
    build_id='pilot-v1-'+sha(encode(signature).encode())[:20]
    report={'build_id':build_id,'fixtures':fixtures,'gates':{f'V{i}':'passed_bounded_pilot' for i in range(1,8)},
            'V8':'outputs_available_for_inspection_no_automatic_expansion','evidence_checks':p.evidence_checks,'field_support_checks':p.field_support_checks,
            'source_inventory':p.inventory,'row_counts':{t:len(rows) for t,rows in p.tables.items()},
            'normalization_outcomes':dict(Counter(t['outcome'] for t in p.tables['transformations'].values())),
            'reference_states':dict(Counter(t['target_availability'] for t in p.tables['source_references'].values())),
            'review_queue_by_stage':dict(Counter(t['stage'] for t in p.tables['review_queue'].values())),
            'review_queue_unit':'issue rows; one owner can have several issues; do not sum as distinct source records',
            'raw_and_prior_artifacts_unchanged':True,'accepted_mappings':0,'clinical_approvals':0,'semantic_merges':0,
            'limitations':['Container-bound snapshots conservatively version members if a file changes.',
                           'Availability states refer to selected pilot output, not remote nonexistence or all archived data.',
                           'Only contract-selected records and transformations processed; no full-dataset validation.',
                           'Temporal fixtures validate key/state mechanics; no live publisher lifecycle changes executed.',
                           'Citation extraction, passage projection, semantic review and graph export remain deferred.']}
    payloads={spec['file']:(''.join(encode(p.tables[t][id])+'\n' for id in sorted(p.tables[t]))).encode() for t,spec in p.contract['tables'].items()}
    payloads['input_manifest.json']=(encode(signature)+'\n').encode()
    payloads['validation_report.json']=(encode(report)+'\n').encode()
    manifest={'build_id':build_id,'contract':{'id':p.contract['contract_id'],'version':p.contract['version'],'sha256':signature['contract_sha256']},
              'signature':signature,'configuration':config,'fingerprint_profile':'raw-bytes-v1','payload_scope':'container_bound_record',
              'source_to_output_lineage':'artifacts -> snapshots -> evidence -> source-scoped rows; transformation evidence links retained',
              'tables':{t:{'file':spec['file'],'row_count':len(p.tables[t]),'status':('emitted' if p.tables[t] else ('empty_no_selected_rows' if spec['pilot']=='as_applicable' else spec['pilot'])),
                           'sha256':sha(payloads[spec['file']]),'bytes':len(payloads[spec['file']])} for t,spec in p.contract['tables'].items()},
              'files':{name:{'sha256':sha(data),'bytes':len(data)} for name,data in payloads.items()},'validation_report':'validation_report.json','raw_files_unchanged':True}
    payloads['manifest.json']=(encode(manifest)+'\n').encode()
    out=root/'data/processed/poc'/build_id
    if write:
        if out.exists():
            if {x.name for x in out.iterdir()}!=set(payloads):raise ValueError('Unexpected existing build files')
            for name,b in payloads.items():
                if (out/name).read_bytes()!=b:raise ValueError('Reproducibility conflict: '+name)
        else:
            import tempfile,os,shutil
            out.parent.mkdir(parents=True,exist_ok=True)
            temp=Path(tempfile.mkdtemp(prefix='.pilot-',dir=out.parent))
            try:
                for name,b in payloads.items():(temp/name).write_bytes(b)
                os.rename(temp,out)
            except BaseException:
                shutil.rmtree(temp,ignore_errors=True);raise
        if p.protected_hashes()!=p.protected:raise ValueError('Protected files changed during write')
    return out,report,p

if __name__=='__main__':
    output,report,_=run(Path(__file__).resolve().parents[1])
    print(output)
    print(encode(report))
