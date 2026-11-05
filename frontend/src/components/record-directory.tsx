import {useState} from 'react'
import {Link, NavLink, useSearchParams} from 'react-router-dom'
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query'
import {ArrowLeft, Database, LoaderCircle, Plus, Search, Users} from 'lucide-react'
import {api, type Datasource, type Person} from '../api'
import {missionDomains} from '../catalog-filters'
import {Button} from './button'

type RecordKind='people'|'datasources'
type CatalogRecord=Person|Datasource
const recordKey=(record:CatalogRecord)=>'email' in record?record.email:record.name
const message=(error:unknown)=>error instanceof Error?error.message:'Unable to load the registry.'

export function RecordDirectory({kind,user,canEdit}:{kind:RecordKind;user:string;canEdit:boolean}) {
  const personnel=kind==='people'
  const [params,setParams]=useSearchParams()
  const q=params.get('q')||''
  const [editing,setEditing]=useState<CatalogRecord|'new'|null>(null)
  const [deleting,setDeleting]=useState<string|null>(null)
  const client=useQueryClient()
  const records=useQuery({queryKey:[user,'/'+kind],queryFn:()=>api<CatalogRecord[]>('/'+kind,user)})
  const remove=useMutation({mutationFn:(key:string)=>api('/'+kind+'/'+encodeURIComponent(key),user,{method:'DELETE'}),onSuccess:()=>{setDeleting(null);void client.invalidateQueries()}})
  const visible=(records.data||[]).filter(record=>{
    const values='email' in record?[record.full_name,record.email,record.organization,record.job_title,...record.areas_of_expertise]:[record.name,record.description,record.domain,record.organization]
    return values.join(' ').toLocaleLowerCase().includes(q.toLocaleLowerCase())
  })
  const Icon=personnel?Users:Database
  return <div className="record-directory">
    <Link className="back" to="/"><ArrowLeft aria-hidden="true" size={16}/>Back to home</Link>
    <div className="page-title"><div><h1>{personnel?'Personnel registry':'Datasource registry'}</h1><p>{personnel?'Find people by organization, job title, and areas of expertise.':'Discover the data sources behind shared Navy capabilities.'}</p></div>{canEdit&&<Button onClick={()=>{setEditing('new');remove.reset();setDeleting(null)}}><Plus aria-hidden="true" size={16}/>{personnel?'Add person':'Add datasource'}</Button>}</div>
    <nav className="record-tabs" aria-label="People and data"><NavLink to="/people"><Users aria-hidden="true" size={17}/>Personnel</NavLink><NavLink to="/datasources"><Database aria-hidden="true" size={17}/>Datasources</NavLink></nav>
    {editing&&<RecordEditor key={editing==='new'?'new':recordKey(editing)} kind={kind} initial={editing==='new'?undefined:editing} user={user} onClose={()=>setEditing(null)}/>}
    <label className="record-search"><Search size={19} aria-hidden="true"/><input aria-label={personnel?'Search personnel':'Search datasources'} placeholder={personnel?'Search names, organizations, or expertise…':'Search datasource names, descriptions, or mission domains…'} value={q} onChange={e=>setParams(e.target.value?{q:e.target.value}:{},{replace:true})}/></label>
    {remove.isError&&<div className="error" role="alert">{message(remove.error)}</div>}
    {records.isPending?<div className="loading" role="status"><LoaderCircle aria-hidden="true" size={22} className="spin"/>Loading {personnel?'personnel':'datasources'}…</div>:records.isError?<div className="error" role="alert">{message(records.error)} <Button variant="outline" onClick={()=>void records.refetch()}>Try again</Button></div>:visible.length?<><p className="record-count">{visible.length} {personnel?'people':'datasources'} in your authorized view</p><div className="record-grid">{visible.map(record=><article className="panel record-card" key={recordKey(record)}>
      <Icon size={24} className="record-icon" aria-hidden="true"/>{'email' in record?<><h2>{record.full_name}</h2><p>{record.job_title}</p><p>{record.organization}</p><p className="record-email">{record.email}</p>{record.work_phone&&<p>Work phone: {record.work_phone}</p>}<div className="tags">{record.areas_of_expertise.map(area=><span key={area}>{area}</span>)}</div></>:<><h2>{record.name}</h2><p>{record.description}</p><p>{record.organization}</p><div className="tags"><span>{record.domain}</span></div></>}
      {canEdit&&<div className="record-actions"><Button variant="outline" onClick={()=>{setEditing(record);setDeleting(null);remove.reset();window.scrollTo({top:0,behavior:'instant'})}}>Edit</Button>{deleting===recordKey(record)?<><Button variant="ghost" disabled={remove.isPending} onClick={()=>remove.mutate(recordKey(record))}>Confirm delete</Button><Button variant="ghost" onClick={()=>setDeleting(null)}>Cancel</Button></>:<Button variant="ghost" onClick={()=>{setDeleting(recordKey(record));remove.reset()}}>Delete</Button>}</div>}
    </article>)}</div></>:<div className="empty"><Icon aria-hidden="true" size={30}/><h2>{q?'No matching records':personnel?'No personnel registered':'No datasources registered'}</h2><p>{q?'Try a different name, organization, or keyword.':'A catalog curator can add the first record.'}</p></div>}
  </div>
}

function RecordEditor({kind,user,initial,onClose}:{kind:RecordKind;user:string;initial?:CatalogRecord;onClose:()=>void}) {
  const personnel=kind==='people'
  const person=initial&&'email' in initial?initial:undefined
  const source=initial&&'description' in initial?initial:undefined
  const [form,setForm]=useState<Record<string,string>>({email:person?.email||'',full_name:person?.full_name||'',organization:initial?.organization||'',job_title:person?.job_title||'',work_phone:person?.work_phone||'',areas_of_expertise:person?.areas_of_expertise.join(', ')||'',name:source?.name||'',description:source?.description||'',domain:source?.domain||'Other',visibility:initial?.visibility||'public',allowed_groups:initial?.allowed_groups.join(', ')||''})
  const client=useQueryClient()
  const terms=(text:string)=>text.split(',').map(term=>term.trim()).filter(Boolean)
  const save=useMutation({mutationFn:()=>{
    const policy={organization:form.organization,visibility:form.visibility,allowed_groups:terms(form.allowed_groups)}
    const body=personnel?{...policy,email:form.email,full_name:form.full_name,job_title:form.job_title,work_phone:form.work_phone||null,areas_of_expertise:terms(form.areas_of_expertise)}:{...policy,name:form.name,description:form.description,domain:form.domain}
    return api('/'+kind+(initial?'/'+encodeURIComponent(recordKey(initial)):''),user,{method:initial?'PATCH':'POST',body:JSON.stringify(body)})
  },onSuccess:()=>{void client.invalidateQueries();onClose()}})

  function field(key:string,label:string,required=true,maxLength=160) {
    return <label key={key}>{label}{!required&&<small> optional</small>}<input type={key==='email'?'email':key==='work_phone'?'tel':'text'} required={required} maxLength={maxLength} disabled={!!initial&&(key==='email'||key==='name')} value={form[key]} onChange={e=>setForm({...form,[key]:e.target.value})}/></label>
  }
  return <form className="panel record-editor" aria-label={personnel?'Personnel record':'Datasource record'} onSubmit={e=>{e.preventDefault();save.mutate()}}>
    <h2>{initial?'Edit':'Add'} {personnel?'person':'datasource'}</h2>
    <div className="form-grid">{personnel?<>{field('email','Email',true,254)}{field('full_name','Full name')}{field('organization','Organization')}{field('job_title','Job title')}{field('work_phone','Work phone',false,80)}{field('areas_of_expertise','Areas of expertise — comma separated',false,6000)}</>:<>{field('name','Datasource name')}{field('organization','Owning organization')}<label>Mission domain<select value={form.domain} onChange={e=>setForm({...form,domain:e.target.value})}>{[...new Set([...missionDomains,form.domain])].map(domain=><option key={domain}>{domain}</option>)}</select></label></>}
      <label>Application access label<select value={form.visibility} onChange={e=>setForm({...form,visibility:e.target.value})}>{['public','internal','group'].map(scope=><option key={scope}>{scope}</option>)}</select></label>
      {form.visibility==='group'&&field('allowed_groups','Authorized demo groups — comma separated',true,4000)}
    </div>
    {!personnel&&<label>Datasource description<textarea required maxLength={5000} rows={3} value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></label>}
    {save.isError&&<div className="error" role="alert">{message(save.error)}</div>}
    <div className="actions"><Button type="submit" disabled={save.isPending}>{save.isPending?'Saving…':personnel?'Save person':'Save datasource'}</Button><Button type="button" variant="ghost" onClick={onClose}>Cancel</Button></div>
  </form>
}
