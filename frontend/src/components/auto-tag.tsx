import {useState} from 'react'
import {useMutation} from '@tanstack/react-query'
import {Check, LoaderCircle, Sparkles} from 'lucide-react'
import {api} from '../api'
import {Button} from './button'
import {projectTypes} from '../catalog-filters'

export type Suggestions={domain:string|null;project_type:string|null;datasets:string[];technologies:string[];evidence:{field:string;suggested_value:string;matched_text:string}[];notice:string}

export function AutoTag({text,user,onApply}:{text:string;user:string;onApply:(value:Suggestions)=>void}) {
  const [draft,setDraft]=useState<Suggestions>(),[reviewed,setReviewed]=useState(false)
  const [source,setSource]=useState(''),[edits,setEdits]=useState({datasets:'',technologies:''})
  const mutation=useMutation({mutationFn:(input:string)=>api<Suggestions>('/discovery/suggest-metadata',user,{method:'POST',body:JSON.stringify({text:input})}),onSuccess:(value,input)=>{setDraft(value);setReviewed(false);setSource(input);setEdits({datasets:value.datasets.join(', '),technologies:value.technologies.join(', ')})}})
  return <section className="auto-tag" aria-label="Editable metadata suggestions"><div className="section-title"><div><strong>Find metadata in your description</strong><p>Review and edit suggestions before applying them.</p></div><Button type="button" variant="outline" disabled={text.trim().length<15||mutation.isPending} onClick={()=>mutation.mutate(text)}>{mutation.isPending?<LoaderCircle className="spin" size={15}/>:<Sparkles size={15}/>}Suggest metadata</Button></div>
    {mutation.error&&<div className="error" role="alert">{mutation.error.message}</div>}
    {draft&&<div className="suggestion-draft"><div className="form-grid"><label>Suggested domain<input value={draft.domain||''} onChange={e=>{setDraft({...draft,domain:e.target.value||null});setReviewed(false)}}/></label><label>Suggested project type<select value={draft.project_type||''} onChange={e=>{setDraft({...draft,project_type:e.target.value||null});setReviewed(false)}}><option value="">Unknown</option>{projectTypes.map(t=><option key={t}>{t}</option>)}</select></label>{(['datasets','technologies'] as const).map(field=><label key={field}>Suggested {field}<input value={edits[field]} onChange={e=>{setEdits({...edits,[field]:e.target.value});setReviewed(false)}}/></label>)}</div><details><summary>Suggestion evidence</summary><ul>{draft.evidence.map((e,i)=><li key={i}>{e.field}: {e.suggested_value} · {e.matched_text}</li>)}</ul></details><label className="checkbox-label"><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>I reviewed these editable suggestions</label><Button type="button" disabled={!reviewed||source!==text} onClick={()=>{onApply({...draft,...Object.fromEntries(Object.entries(edits).map(([k,v])=>[k,v.split(',').map(x=>x.trim()).filter(Boolean)]))});setDraft(undefined)}}><Check size={15}/>Apply reviewed suggestions</Button><p className="fine-print">{source!==text?'Description changed; refresh suggestions before applying.':draft.notice}</p></div>}
  </section>
}
