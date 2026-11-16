"""Fixed graph-query baseline. Accepts requests only, never expected evidence sets."""
from decimal import Decimal
from kg_evaluation_common import warning_unit

def retrieve(g,request):
 category=request['category'];topic=request['topic'];mid=request.get('monograph_id');primary={};context={}
 result=dict(question_id=request['question_id'],status='source_evidence_only',primary=[],context=[],clinical_approval=False,product_applicability_established=False,equivalence_established=False,recommended_product=None,recommended_dose=None,limitations=['Captured source evidence only; no independent clinical approval or personal recommendation.'])
 def put(i,source,node_id=None,edge=None,role='primary',extra=None,path=None):
  dest=primary if role=='primary' else context;n=g.nodes[node_id] if node_id else None
  packet=dict(unit_id=i,source=source,node_id=node_id,evidence_ids=n['evidence_ids'] if n else edge['evidence_ids'],path_edge_ids=path or ([edge['id']] if edge else []),data=n['properties'] if n else dict(edge['properties'],relation_type=edge['type'],mapping_id=edge['mapping_id'],confidence=edge['confidence']))
  if extra:packet['extra']=extra
  if i not in dest:dest[i]=packet
 def warn(native):
  lid=g.labels[native]
  for e in g.out[(lid,'HAS_ASSERTION')]:
   n=g.nodes[e['end_id']];p=n['properties'];f=p['original_fields']
   # Deliberately simple v1 classifier: source Precautions type only. No gold exceptions.
   if p['kind']=='label_statement' and f.get('type','').casefold().startswith('precautions'):
    put(warning_unit(native,f.get('notes','')),'DSLD',n['id'],path=[e['id']],extra={'label_id':native})
 def clinical(kind=None,claim_id=None):
  for e in g.out[(mid,'HAS_PENDING_CLAIM')]:
   n=g.nodes[e['end_id']];p=n['properties']
   if claim_id and n['id']!=claim_id:continue
   if kind and p['original_fields']['claim_type']!=kind:continue
   support=g.out[(n['id'],'SUPPORTED_BY_EXCERPT')]
   put(n['id'],'NatMed',n['id'],path=[e['id']]+[s['id'] for s in support],extra={'monograph_id':mid,'source_title':g.nodes[mid]['properties']['display_title']})
 def quantity(native):
  lid=g.labels[native];ids=g.occurrences(lid,topic)
  for e in g.out[(lid,'HAS_ASSERTION')]:
   n=g.nodes[e['end_id']];p=n['properties']
   if p['kind']=='composition' and p['occurrence_id'] in ids:
    basis=g.out[(n['id'],'HAS_SERVING_BASIS')]
    put(n['id'],'DSLD',n['id'],path=[e['id']]+[s['id'] for s in basis],extra={'label_id':native})
 def maps(native,kinds):
  ids=g.occurrences(g.labels[native],topic)
  for i in ids:
   for kind in kinds:
    for e in g.out[(i,kind)]:
     if e['confidence']=='High' and e['mapping_id']:put(e['mapping_id'],'reviewed_mapping',edge=e)
 if category=='product_label_warnings':warn(request['label_ids'][0])
 elif category.startswith('natmed_'):clinical(category.removeprefix('natmed_'))
 elif category=='quantity_basis':quantity(request['label_ids'][0])
 elif category=='identity_scope':maps(request['label_ids'][0],['DENOTES_CONCEPT','EXACT_MATERIAL_MATCH'])
 elif category=='product_clinical_applicability':
  warn(request['label_ids'][0]);maps(request['label_ids'][0],['RELATED_INGREDIENT_SUBJECT','RELATED_BOTANICAL_SUBJECT']);clinical('safety');result['status']='related_source_evidence_only'
 elif category=='reddit_direct_context':
  tid=g.topics[topic]
  for relation,role in [('MENTIONS_TOPIC','primary'),('INHERITED_THREAD_TOPIC','context')]:
   for e in g.inc[(tid,relation)]:put(e['start_id'],'Reddit',e['start_id'],role=role,path=[e['id']],extra={'relation_type':relation,'topic':topic,'association':e['properties']})
 elif category=='category_not_equivalence':
  for e in g.edges.values():
   if e['type']=='MEMBER_OF_CATEGORY' and e['confidence']=='High':put(e['mapping_id'],'reviewed_mapping',edge=e)
  result['limitations'].append('Category membership does not establish material or product equivalence.')
 elif category=='null_preservation':clinical(claim_id=request['claim_id'])
 elif category=='label_vs_clinical':warn(request['label_ids'][0]);clinical('safety');result['status']='source_separated_comparison'
 elif category=='unsupported_recommendation':
  result['status']='insufficient_information';result['limitations'].append('Prescription medicine and relevant personal context are unspecified; personal safety cannot be determined.')
 elif category=='navigation_vs_strain':
  tid=g.topics[topic]
  for e in g.inc[(tid,'LABEL_TITLE_MENTIONS_TOPIC')]:put(e['start_id'],'DSLD',e['start_id'],path=[e['id']])
  for e in g.inc[(tid,'INGREDIENT_NAME_MENTIONS_TOPIC')]:
   for label in g.inc[(e['start_id'],'DECLARES_OCCURRENCE')]:put(label['start_id'],'DSLD',label['start_id'],path=[label['id'],e['id']])
  result['declared_organisms_and_ingredients']={i:[dict(node_id=e['end_id'],original_name=g.nodes[e['end_id']]['properties']['original_name'],source_role=g.nodes[e['end_id']]['properties']['role'],evidence_ids=g.nodes[e['end_id']]['evidence_ids']) for e in g.out[(i,'DECLARES_OCCURRENCE')]] for i in primary}
 elif category=='comparison_and_abstention':
  for native in request['label_ids']:quantity(native)
  normalized=[]
  for packet in primary.values():
   p=packet['data'];gate=p.get('quantity_comparison')
   if gate and gate['status']=='eligible_for_scoped_comparison':normalized.extend(t['normalized_value'] for t in p['transformations'] if t['destination_field']=='mass_comparison' and t['normalized_value'])
  keys=['basis_quantity','basis_unit','operator','serving_order','unit'];equivalent=len(normalized)==2 and Decimal(normalized[0]['amount'])==Decimal(normalized[1]['amount']) and all(normalized[0][k]==normalized[1][k] for k in keys)
  other=[]
  for native in request['label_ids']:
   entries=[g.nodes[e['end_id']]['properties'] for e in g.out[(g.labels[native],'DECLARES_OCCURRENCE')] if g.nodes[e['end_id']]['properties']['role'] in ['other_ingredient','other_form']]
   other.append(sorted((p['original_name'],str(p['attributes'])) for p in entries))
  result['quantity_comparison']=dict(equivalent_declared_mass_and_basis=equivalent,other_ingredient_declarations_differ=other[0]!=other[1],scope='Declared quantities only, not recommended doses or product equivalence')
  result['status']='partial_answer_comparative_abstention';result['limitations'].append('No product-comparative effectiveness conclusion is established.')
 else:raise ValueError(category)
 result['primary']=list(primary.values());result['context']=list(context.values());return result
