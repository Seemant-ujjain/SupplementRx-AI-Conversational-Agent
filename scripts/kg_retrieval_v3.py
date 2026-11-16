"""Conservative content/source relevance revision; no evaluation labels, example IDs or expected sets."""
import re
from kg_evaluation_common import warning_unit
from kg_retrieval_baseline import retrieve as retrieve_v1

WARNING_CUES = [
 r'\b(?:warning|caution)\s*:',
 r'\bdo not\s+(?:use|take|exceed|consume|drive|operate|snack|accept)',
 r'\bnot\s+(?:intended|recommended|suitable)\s+for\s+(?:use|children|persons|pregnant)',
 r'\b(?:keep|store)\b.{0,35}\bout of (?:the )?reach\b',
 r'\b(?:consult|discuss|contact|ask|get the consent of)\b.{0,100}\b(?:physician|doctor|health.?care|health care|practitioner|provider)',
 r'\b(?:discontinue|stop)\s+(?:use|using|taking)',
 r'\b(?:avoid|limit)\s+(?:use|using|taking|consuming|doses?)',
 r'\bread\b.{0,30}\blabel\b.{0,30}\bbefore use\b',
 r'\b(?:may (?:cause|produce)|risk of|accidental overdose|allergic to)\b',
 r'\b(?:take|use)\b.{0,45}\b(?:hours? before|hours? after|before or after)\b.{0,45}\bmedications?\b',
 r'\b(?:for (?:healthy )?adults?(?: use)? only|for adults[, ]|adults take|not for children)\b'
]

def warning_relevance(fields):
 text=fields.get('notes') or '';typ=(fields.get('type') or '').casefold()
 # These categories are outside warning/use-restriction scope; no prose editing.
 if typ in {'storage','fda disclaimer statement','fda statement of identity'}:return 'exclude','non_warning_statement_category'
 # Reporting contacts alone are optional administrative support, not precautions.
 if re.search(r'\b(?:report a serious adverse event|obtain product information)\b',text,re.I) and not re.search(r'\b(?:do not|discontinue|stop using|seek|emergency)\b',text,re.I):return 'context','reporting_contact'
 if re.fullmatch(r'\s*(?:warning|caution)[:.! ]*see (?:the )?(?:side |back )?panel[.! ]*',text,re.I):return 'context','warning_locator_only'
 if any(re.search(pattern,text,re.I|re.S) for pattern in WARNING_CUES):return 'primary','explicit_warning_or_use_restriction'
 if 'allerg' in typ and re.search(r'\b(?:contains?|process|manufactured|facility|allerg)',text,re.I):return 'primary','source_allergen_notice'
 if typ.startswith('precautions'):
  if re.search(r'\bformulated\b.{0,80}\b(?:support|promote)\b',text,re.I|re.S):return 'exclude','formulation_marketing_without_warning_cue'
  return 'primary','conservative_source_precaution_fallback'
 if re.search(r'\b(?:not required or recommended|not recommended|check with)\b',text,re.I):return 'primary','negative_recommendation_or_consultation'
 if 'suggested' in typ or 'direction' in typ:return 'context','routine_directions'
 return 'exclude','no_explicit_warning_content'

def clinical_role(fields):
 if fields['claim_type']=='adverse_effect' and (fields.get('adverse_effect_category') or '').strip().casefold()=='general':return 'context','general_tolerability_context'
 if fields['claim_type']=='dose':
  d=fields.get('dose') or {};numeric=any(d.get(k) is not None for k in ['value','minimum','maximum']);text=d.get('text') or ''
  directive=bool(re.search(r'\b(?:advise|avoid|do not|should not|must not|limit|exceed)\b',text,re.I))
  general=bool(re.search(r'\brecommendations?\b.{0,35}\bvary\b|\bdos(?:ing|e)\b.{0,30}\bnot established\b',text,re.I))
  if general and not numeric and not directive:return 'context','explicit_general_dose_context'
 return 'primary','requested_clinical_annotation'

def retrieve(g,request):
 response=retrieve_v1(g,request)
 warning_categories={'product_label_warnings','product_clinical_applicability','label_vs_clinical'}
 if request['category'] in warning_categories:
  response['primary']=[p for p in response['primary'] if not p['unit_id'].startswith('warning:')]
  response['context']=[p for p in response['context'] if not p['unit_id'].startswith('warning:')]
  primary={p['unit_id']:p for p in response['primary']};context={p['unit_id']:p for p in response['context']}
  for native in request['label_ids']:
   for e in g.out[(g.labels[native],'HAS_ASSERTION')]:
    n=g.nodes[e['end_id']];p=n['properties']
    if p['kind']!='label_statement':continue
    role,reason=warning_relevance(p['original_fields'])
    if role=='exclude':continue
    unit=warning_unit(native,p['original_fields'].get('notes',''));packet=dict(unit_id=unit,source='DSLD',node_id=n['id'],evidence_ids=n['evidence_ids'],path_edge_ids=[e['id']],data=p,extra=dict(label_id=native,relevance_role=role,relevance_reason=reason))
    if role=='primary':primary.setdefault(unit,packet);context.pop(unit,None)
    elif unit not in primary:context.setdefault(unit,packet)
  response['primary']=list(primary.values());response['context']=list(context.values())
 if request['category'].startswith('natmed_'):
  keep=[]
  for p in response['primary']:
   role,reason=clinical_role(p['data']['original_fields']);p['extra'].update(relevance_role=role,relevance_reason=reason)
   (response['context'] if role=='context' else keep).append(p)
  response['primary']=keep
 response['relevance_revision']='conservative-rules-v3';return response
