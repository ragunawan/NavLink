import React, {createContext, useContext, useRef, useState} from 'react'
import {createRoot} from 'react-dom/client'
import {BrowserRouter, Link, Route, Routes, useLocation, useNavigate, useParams, useSearchParams} from 'react-router-dom'
import {QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient} from '@tanstack/react-query'
import {ArrowLeft, ArrowRight, ArrowUpRight, BookOpen, Check, CircleHelp, Database, GitCompareArrows, Layers3, LoaderCircle, LockKeyhole, Plus, Search, ShieldCheck, Sparkles, Users, Workflow, X} from 'lucide-react'
import {api, type Comparison, type Hit, type Project, type SearchResult} from './api'
import {AutoTag} from './components/auto-tag'
import {Button} from './components/button'
import './styles.css'
import './homepage.css'
import {DiscoveryAssistant} from './discovery-assistant'
import {CheckBeforeBuild} from './check-before-build'
import {ProjectComparison} from './components/project-comparison'
import {AppHeader} from './components/app-header'
import {HomePage} from './components/homepage'
import {DiscoveryDirectory} from './components/discovery-directory'
import {projectTypes as types, projectStatuses as statuses} from './catalog-filters'

const PROJECT_MOTTO = 'Create once, discover everywhere, improve together.'
const queryClient = new QueryClient({defaultOptions:{queries:{retry:1,staleTime:15000,refetchOnWindowFocus:false}}})
const AppContext = createContext<{user:string;canEdit:boolean;selected:string[];toggle:(id:string)=>void}>({user:'visitor',canEdit:false,selected:[],toggle:()=>{}})
const useApp = () => useContext(AppContext)
const domains = ['Financial management','Logistics','Readiness','Maintenance','Personnel','Acquisition','Cybersecurity']

function useApi<T>(path:string, enabled=true) {const {user}=useApp();return useQuery({queryKey:[user,path],queryFn:()=>api<T>(path,user),enabled})}
function ErrorBox({error}:{error:unknown}) {return error ? <div role="alert" className="error">{error instanceof Error ? error.message : 'Unable to load data. Check that the local API is running.'}</div> : null}
function Loading() {return <div className="loading" role="status"><LoaderCircle size={22} className="spin"/> Loading local catalog…</div>}
function Status({value}:{value:string}) {return <span className={'status status-'+value.toLowerCase().replaceAll(' ','-')}><span/>{value}</span>}
function PageTitle({eyebrow,title,description,action}:{eyebrow:string;title:string;description:string;action?:React.ReactNode}) {return <div className="page-title"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>}
function SearchBox({initial=''}:{initial?:string}) {
 const [value,setValue]=useState(initial);const input=useRef<HTMLInputElement>(null);const navigate=useNavigate();const [params]=useSearchParams()
 return <form className="searchbox" role="search" onSubmit={e=>{e.preventDefault();const next=new URLSearchParams(params);if(value.trim())next.set('q',value.trim());else next.delete('q');navigate('/catalog'+(next.size?'?'+next:''))}}><Search size={22} aria-hidden="true"/><input ref={input} aria-label="Search capabilities" maxLength={3000} placeholder="Describe a mission need, capability, or dataset…" value={value} onChange={e=>setValue(e.target.value)}/>{value&&<button type="button" className="catalog-clear" aria-label="Clear search" onClick={()=>{setValue('');input.current?.focus()}}><X size={18}/></button>}<Button type="submit">Search <ArrowRight size={16}/></Button></form>
}

function ProjectCard({project:p,hit,compact=false}:{project:Project;hit?:Hit;compact?:boolean}) {
 const {selected,toggle}=useApp()
 return <article className={'project-card '+(compact?'compact':'')}>
  <div className="card-top"><span className="type-label"><Layers3 size={15}/>{p.project_type}</span><Status value={p.status}/></div>
  <h3><Link to={'/projects/'+p.id}>{p.name}<ArrowUpRight size={17}/></Link></h3>
  <div className="organization">{p.organization}</div><p>{p.mission_problem}</p>
  {hit && <div className="evidence"><span><Sparkles size={13}/> WHY IT MATCHES · RANK {hit.rank}</span><p>{hit.evidence[0]}</p><small>{hit.inference}</small></div>}
  <div className="tags"><span>{p.domain}</span>{p.technologies.slice(0,2).map(t=><span key={t}>{t}</span>)}</div>
  <div className="card-bottom"><Link to={'/projects/'+p.id}>View capability <ArrowRight size={15}/></Link><button className={'compare-toggle '+(selected.includes(p.id)?'chosen':'')} aria-label={'Compare '+p.name} aria-pressed={selected.includes(p.id)} onClick={()=>toggle(p.id)}><GitCompareArrows size={15}/>{selected.includes(p.id)?'Selected':'Compare'}</button></div>
 </article>
}

function Dashboard() {
 const {user}=useApp()
 return <HomePage user={user} renderProject={project=><ProjectCard project={project} compact/>}/>
}

function Catalog() {
 const [params,setParams]=useSearchParams(); const q=params.get('q')||''
 const mode=params.get('mode')||'hybrid'
 const domainQuery=useApi<string[]>('/domains'),orgQuery=useApi<string[]>('/organizations')
 const filters=['domain','project_type','organization','status'];const qs=new URLSearchParams(params);qs.delete('q');qs.delete('mode')
 const list=useApi<Project[]>('/projects?'+qs,!q)
 const results=useApi<SearchResult>('/search?'+params,!!q)
 function set(key:string,value:string) {const p=new URLSearchParams(params);if(value)p.set(key,value);else p.delete(key);setParams(p)}
 const data=q?results.data?.results.map(h=>({project:h.project,hit:h})):list.data?.map(project=>({project,hit:undefined}))
 const pending=q?results.isPending:list.isPending
 return <><PageTitle eyebrow="THE SHARED CATALOG" title="Discover capabilities" description="Search by mission, explore by domain, and follow the evidence." action={<Button asChild variant="outline"><Link to="/projects/new"><Plus size={16}/>Register project</Link></Button>}/><SearchBox key={q} initial={q}/>
 <div className="catalog-layout"><aside className="filters"><div className="section-title"><h3>Refine discovery</h3><button className="text-button" onClick={()=>setParams(q?{q}: {})}>Reset</button></div>{filters.map((key,i)=><label key={key}>{['Mission domain','Project type','Organization','Project status'][i]}<select value={params.get(key)||''} onChange={e=>set(key,e.target.value)}><option value="">All {['domains','types','organizations','statuses'][i]}</option>{[domainQuery.data||[],types,orgQuery.data||[],statuses][i].map(x=><option key={x}>{x}</option>)}</select></label>)}<div className="filter-note"><ShieldCheck size={19}/><p>Your identity determines which capabilities and contacts are discoverable.</p></div></aside>
 <section><div className="results-heading"><span>{pending?'Searching…':`${q?results.data?.total??0:data?.length??0} ${q?'ranked matches':'capabilities'}`}{q&&results.data&&<small> · {results.data.elapsed_ms} ms</small>}</span><label className="mode-label">Search mode<select value={mode} onChange={e=>set('mode',e.target.value)}>{['hybrid','keyword','semantic'].map(m=><option key={m} value={m}>{m[0].toUpperCase()+m.slice(1)}</option>)}</select></label></div><ErrorBox error={q?results.error:list.error}/>{pending?<Loading/>:data?.length?<div className="search-cards">{data.map(({project,hit})=><ProjectCard key={project.id} project={project} hit={hit}/>)}</div>:<div className="empty"><Search size={32}/><h2>No capabilities found</h2><p>Try a broader mission description or clear a filter.</p></div>}{q&&results.data&&<p className="fine-print">Encoder: {results.data.encoder}. Ranking is a relative ordering, not a confidence percentage.</p>}</section></div></>
}

function ProjectDetail() {
 const {id}=useParams();const {user,canEdit,selected,toggle}=useApp();const navigate=useNavigate();const client=useQueryClient();const [confirm,setConfirm]=useState(false)
 const {data:p,error,isPending}=useApi<Project>('/projects/'+id)
 const relations=useApi<SearchResult>('/projects/'+id+'/related',!!p)
 const remove=useMutation({mutationFn:()=>api('/projects/'+id,user,{method:'DELETE'}),onSuccess:()=>{client.invalidateQueries();navigate('/catalog')}})
 if(isPending)return <Loading/>;if(!p)return <ErrorBox error={error}/>
 return <><Link className="back" to="/catalog"><ArrowLeft size={16}/>Back to catalog</Link><PageTitle eyebrow={`${p.project_type.toUpperCase()} · SYNTHETIC RECORD`} title={p.name} description={p.organization} action={<div className="actions"><Button asChild variant="outline"><Link to={'/check?project='+p.id}><Workflow size={16}/>Check before you build</Link></Button><Button variant="outline" onClick={()=>toggle(p.id)}><GitCompareArrows size={16}/>{selected.includes(p.id)?'Remove comparison':'Add to comparison'}</Button>{canEdit&&<Button asChild><Link to={'/projects/'+p.id+'/edit'}>Edit project</Link></Button>}</div>}/>
 <div className="detail-layout"><div><section className="panel detail-panel"><div className="detail-meta"><Status value={p.status}/><span>{p.domain}</span><span>Updated {p.last_updated}</span></div><h2>Mission problem</h2><p className="mission-text">{p.mission_problem}</p><h2>About this capability</h2><p>{p.description}</p><h2>Technical approach</h2><p>{p.technical_summary||'Not provided.'}</p><div className="tags">{p.technologies.map(t=><span key={t}>{t}</span>)}</div><h2>Intended users</h2><p>{p.intended_users.join(', ')||'Unknown — not stated in the catalog.'}</p><h2>Stated use cases</h2><ul>{p.use_cases.map(t=><li key={t}>{t}</li>)}</ul><h2>Associated datasets</h2>{p.datasets.length?p.datasets.map(d=><div className="dataset-row" key={d.name}><Database size={19}/><div><strong>{d.name}</strong><p>{d.description}</p></div></div>):<p>No datasets stated.</p>}<h2>Keywords</h2><div className="tags">{p.tags.map(t=><span key={t}>{t}</span>)}</div></section>
 <section className="related-section"><div className="section-title"><div><span className="eyebrow">FOLLOW THE CONNECTIONS</span><h2>Related capabilities</h2></div></div><ErrorBox error={relations.error}/>{relations.isPending?<Loading/>:<div className="search-cards">{relations.data?.results.map(h=><ProjectCard key={h.project.id} project={h.project} hit={h}/>)}</div>}</section></div>
 <aside><section className="panel detail-panel"><h2><Users size={18}/>Approved contacts</h2>{p.contacts.length?p.contacts.map(c=><div className="contact" key={c.method}><strong>{c.name}</strong><small>{c.role}</small><span>{c.method}</span></div>):<p>Approved POC information is unavailable for this view.</p>}{p.contacts_withheld&&<p className="fine-print">Some contact information is not available to this identity.</p>}<h2><BookOpen size={18}/>Resources & access</h2>{[['Documentation',p.documentation_url],['Repository',p.repository_url],['Demonstration',p.demo_url]].map(([label,url])=>url&&<a className="resource" key={label} href={url} target="_blank" rel="noreferrer">{label}<ArrowUpRight size={16}/></a>)}<p className="fine-print">Reserved .example links identify fictional resources.</p><p>{p.access_instructions}</p><h2>Reuse considerations</h2>{[['License / terms',p.license],['Deployment',p.deployment],['Integration',p.integration]].map(([k,v])=><div className="reuse-field" key={k}><small>{k}</small><p>{v||'Unknown — confirm with the owner.'}</p></div>)}<div className="notice"><LockKeyhole size={16}/><div><strong>{p.visibility} demo access</strong><p>{p.availability}. Application access label; not an official classification marking.</p></div></div></section>{canEdit&&<div className="delete-area"><Button variant="ghost" onClick={()=>confirm?remove.mutate():setConfirm(true)}>{remove.isPending?'Deleting…':confirm?'Confirm delete project':'Delete project'}</Button>{confirm&&<button className="text-button" onClick={()=>setConfirm(false)}>Cancel</button>}<ErrorBox error={remove.error}/></div>}</aside></div></>
}


function Compare() {
 const {selected,user}=useApp()
 const result=useQuery({queryKey:[user,'compare',selected],queryFn:()=>api<Comparison>('/projects/compare',user,{method:'POST',body:JSON.stringify({project_ids:selected})}),enabled:selected.length>=2})
 return <><PageTitle eyebrow="EVALUATE THE OVERLAP" title="Compare capabilities" description="A side-by-side view of stated metadata, differences, and questions to resolve."/>{selected.length<2?<div className="empty"><GitCompareArrows size={32}/><h2>Select two or three capabilities</h2><p>Use Compare on any catalog card to add a project.</p><Button asChild><Link to="/catalog">Browse catalog</Link></Button></div>:result.isPending?<Loading/>:result.data?<><section className="panel"><ProjectComparison comparison={result.data}/></section></>:<ErrorBox error={result.error}/>}</>
}

const split=(s:string)=>s.split(',').map(x=>x.trim()).filter(Boolean)
function RegistryForm() {
 const {id}=useParams();const {canEdit}=useApp();const existing=useApi<Project>('/projects/'+id,!!id)
 if(!canEdit)return <><PageTitle eyebrow="PROJECT REGISTRY" title="Contribute to the shared picture" description="Select Catalog curator in the demo identity menu to register or edit projects."/><div className="notice"><LockKeyhole size={20}/><p>Read access and edit permissions are enforced by the local API. Identity selection is a non-production demonstration.</p></div></>
 if(id&&existing.isPending)return <Loading/>
 if(id&&!existing.data)return <ErrorBox error={existing.error}/>
 return <RegistryEditor key={id||'new'} initial={existing.data}/>
}
function RegistryEditor({initial}:{initial?:Project}) {
 const {user}=useApp();const navigate=useNavigate();const client=useQueryClient()
 const [form,setForm]=useState<Record<string,string>>({name:initial?.name||'',description:initial?.description||'',mission_problem:initial?.mission_problem||'',project_type:initial?.project_type||'Application',domain:initial?.domain||'Maintenance',organization:initial?.organization||'',status:initial?.status||'Concept',technical_summary:initial?.technical_summary||'',technologies:initial?.technologies.join(', ')||'',tags:initial?.tags.join(', ')||'',datasets:initial?.datasets.map(d=>d.name+' | '+d.description).join('\n')||'',use_cases:initial?.use_cases.join('\n')||'',intended_users:initial?.intended_users.join(', ')||'',repository_url:initial?.repository_url||'',documentation_url:initial?.documentation_url||'',demo_url:initial?.demo_url||'',access_instructions:initial?.access_instructions||'',availability:initial?.availability||'Synthetic demonstration only',visibility:initial?.visibility||'public',allowed_groups:initial?.allowed_groups.join(', ')||'',license:initial?.license||'',deployment:initial?.deployment||'',integration:initial?.integration||''})
 const [contacts,setContacts]=useState<Project['contacts']>(initial?.contacts||[]);const [checked,setChecked]=useState(false);const [overlap,setOverlap]=useState<string[]|null>(null)
 const mutation=useMutation({mutationFn:async()=>{const payload={...form,technologies:split(form.technologies),tags:split(form.tags),intended_users:split(form.intended_users),allowed_groups:split(form.allowed_groups),use_cases:form.use_cases.split('\n').filter(Boolean),contacts,datasets:form.datasets.split('\n').filter(Boolean).map(x=>{const [name,...description]=x.split('|');return {name:name.trim(),description:description.join('|').trim()}}),last_updated:new Date().toISOString().slice(0,10),repository_url:form.repository_url||null,documentation_url:form.documentation_url||null,demo_url:form.demo_url||null,license:form.license||null,deployment:form.deployment||null,integration:form.integration||null};return api<Project>(initial?'/projects/'+initial.id:'/projects',user,{method:initial?'PATCH':'POST',body:JSON.stringify(payload)})},onSuccess:p=>{client.invalidateQueries();navigate('/projects/'+p.id)}})
 const duplicate=useMutation({mutationFn:()=>api<{candidates:{project:Project}[]}>('/discovery/check-duplicate',user,{method:'POST',body:JSON.stringify({description:form.mission_problem+' '+form.description})}),onSuccess:data=>{setOverlap(data.candidates.filter(c=>c.project.id!==initial?.id).map(c=>c.project.name));setChecked(true)}})
 function field(key:string,label:string,options?:string[],multiline=false) {return <label key={key}>{label}{options?<select value={form[key]} onChange={e=>{setForm({...form,[key]:e.target.value});setChecked(false)}}>{options.map(v=><option key={v}>{v}</option>)}</select>:multiline?<textarea required={['description','mission_problem'].includes(key)} rows={key==='contacts'?5:3} value={form[key]} onChange={e=>{setForm({...form,[key]:e.target.value});setChecked(false)}}/>:<input required={['name','organization'].includes(key)} type={key.endsWith('_url')?'url':'text'} value={form[key]} onChange={e=>{setForm({...form,[key]:e.target.value});setChecked(false)}}/>}</label>}
 return <><PageTitle eyebrow="CONTRIBUTE A CAPABILITY" title={initial?'Edit project':'Register a project'} description="Use fictional, approved demonstration metadata only. All records are marked synthetic."/><form className="panel registry-form" onSubmit={e=>{e.preventDefault();if(!checked){duplicate.mutate();return}mutation.mutate()}}><div className="form-grid">{field('name','Project name')}{field('organization','Fictional owning organization')}{field('project_type','Project type',types)}{field('domain','Mission domain')}{field('status','Project status',statuses)}{field('visibility','Application access label',['public','internal','group'])}</div>{field('mission_problem','Mission problem',undefined,true)}{field('description','Description',undefined,true)}<AutoTag text={form.description+' '+form.mission_problem} user={user} onApply={s=>{setChecked(false);setForm({...form,domain:s.domain||form.domain,project_type:s.project_type||form.project_type,tags:s.tags.join(', '),technologies:s.technologies.join(', '),datasets:s.datasets.map(name=>name+' | ').join('\n')})}}/>{field('technical_summary','Technical approach',undefined,true)}<div className="form-grid">{field('intended_users','Intended users — comma separated')}{field('technologies','Technologies — comma separated')}{field('tags','Tags — comma separated')}{field('allowed_groups','Authorized demo groups — comma separated')}{field('availability','Availability / handling note')}</div>{field('datasets','Datasets — one per line: name | description',undefined,true)}{field('use_cases','Stated use cases — one per line',undefined,true)}<fieldset className="contacts-editor"><legend>Approved contacts</legend>{contacts.map((c,i)=><div className="contact-editor form-grid" key={i}>{(['name','role','method'] as const).map(key=><label key={key}>{key==='method'?'Approved contact method':key==='name'?'Fictional contact name':'Contact role'}<input required value={c[key]} onChange={e=>setContacts(contacts.map((x,j)=>i===j?{...x,[key]:e.target.value}:x))}/></label>)}<label>Contact visibility<select value={c.visibility} onChange={e=>setContacts(contacts.map((x,j)=>i===j?{...x,visibility:e.target.value}:x))}>{['public','internal','group'].map(v=><option key={v}>{v}</option>)}</select></label><Button type="button" variant="ghost" onClick={()=>setContacts(contacts.filter((_,j)=>i!==j))}>Remove contact</Button></div>)}<Button type="button" variant="outline" onClick={()=>setContacts([...contacts,{name:'',role:'Project liaison',method:'',visibility:'public'}])}><Plus size={15}/>Add approved contact</Button></fieldset><div className="form-grid">{field('repository_url','Repository URL')}{field('documentation_url','Documentation URL')}{field('demo_url','Demonstration URL')}{field('license','License / reuse terms')}{field('deployment','Deployment information')}{field('integration','Integration compatibility')}</div>{field('access_instructions','Access request instructions',undefined,true)}{overlap&&<div className="notice"><CircleHelp size={20}/><p>Check before you build found these leads: {overlap.join(', ')||'No evidence-backed matches'}. Review the catalog before proceeding; duplication is a human determination.</p></div>}<ErrorBox error={mutation.error||duplicate.error}/><div className="actions"><Button disabled={mutation.isPending||duplicate.isPending} type="submit">{checked?<><Check size={17}/>Save project</>:<><Search size={17}/>Check for existing capabilities</>}</Button><Button variant="ghost" type="button" onClick={()=>navigate('/catalog')}>Cancel</Button></div></form></>
}

function App() {
 const identities=useQuery({queryKey:['identities'],queryFn:()=>api<{id:string;label:string;editor:boolean}[]>('/identities','visitor')})
 const [user,setUser]=useState('visitor');const canEdit=identities.data?.find(i=>i.id===user)?.editor??false
 const [selected,setSelected]=useState<string[]>([])
 const location=useLocation()
 const toggle=(id:string)=>setSelected(ids=>ids.includes(id)?ids.filter(x=>x!==id):ids.length<3?[...ids,id]:ids)
 return <AppContext.Provider value={{user,canEdit,selected,toggle}}>
  <a className="skip-link" href="#main">Skip to content</a>
  <div className="portal-shell">
   <AppHeader user={user} identities={identities.data} selectedCount={selected.length} onIdentityChange={value=>{setUser(value);setSelected([]);queryClient.clear()}}/>
   <main id="main" tabIndex={-1} key={user} className={location.pathname==='/'?'portal-main portal-home':'portal-main'}>
    <ErrorBox error={identities.error}/>
    <Routes>
     <Route path="/" element={<Dashboard/>}/>
     <Route path="/catalog" element={<Catalog/>}/>
     <Route path="/domains" element={<DiscoveryDirectory kind="domains" user={user}/>}/>
     <Route path="/organizations" element={<DiscoveryDirectory kind="organizations" user={user}/>}/>
     <Route path="/projects/new" element={<RegistryForm/>}/>
     <Route path="/projects/:id/edit" element={<RegistryForm/>}/>
     <Route path="/projects/:id" element={<ProjectDetail/>}/>
     <Route path="/check" element={<CheckBeforeBuild user={user}/>}/>
     <Route path="/assistant" element={<DiscoveryAssistant user={user}/>}/>
     <Route path="/compare" element={<Compare/>}/>
     <Route path="*" element={<div className="empty"><h1>Page not found</h1><Link to="/">Return to overview</Link></div>}/>
    </Routes>
   </main>
   <footer className="portal-footer"><div><Link to="/" className="footer-brand">NavyLINK</Link><span>{PROJECT_MOTTO}</span></div><div><span className="footer-demo"><Database size={13} aria-hidden="true"/>Synthetic demonstration data</span><span>Demo identity is not production authentication</span></div></footer>
   {selected.length>0&&<div className="comparison-tray"><GitCompareArrows size={18}/><strong>{selected.length} of 3 selected</strong><Link to="/compare">Compare capabilities <ArrowRight size={15}/></Link><button aria-label="Clear comparison" onClick={()=>setSelected([])}><X size={17}/></button></div>}
  </div>
 </AppContext.Provider>
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={queryClient}><BrowserRouter><App/></BrowserRouter></QueryClientProvider></React.StrictMode>)
