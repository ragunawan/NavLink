import React, {createContext, useContext, useRef, useState} from 'react'
import {createRoot} from 'react-dom/client'
import {BrowserRouter, Link, Route, Routes, useLocation, useNavigate, useParams, useSearchParams} from 'react-router-dom'
import {QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient} from '@tanstack/react-query'
import {ArrowLeft, BookOpen, Check, Database, GitCompareArrows, Layers3, LoaderCircle, LockKeyhole, Plus, Search, ShieldCheck, Sparkles, Users, Workflow, X} from 'lucide-react'
import {api, type Comparison, type Hit, type Project, type ProjectPage, type SearchResult} from './api'
import {Button} from './components/button'
import './styles.css'
import './homepage.css'
import {DiscoveryAssistant} from './discovery-assistant'
import {CheckBeforeBuild} from './check-before-build'
import {ProjectComparison} from './components/project-comparison'
import {AppHeader} from './components/app-header'
import {HomePage} from './components/homepage'
import {DiscoveryDirectory} from './components/discovery-directory'
import {projectTypes as types, projectStatuses as statuses, searchModes} from './catalog-filters'
import {ProjectMetadata} from './components/project-metadata'
import {RegistryEditor} from './components/registry-editor'
import {RecordDirectory} from './components/record-directory'
import {CatalogChatBubble} from './components/catalog-chat-bubble'
import './data-fields.css'

const PROJECT_MOTTO = 'Create once, discover everywhere, improve together.'
const queryClient = new QueryClient({defaultOptions:{queries:{retry:1,staleTime:15000,refetchOnWindowFocus:false}}})
const AppContext = createContext<{user:string;canEdit:boolean;selected:string[];toggle:(id:string)=>void}>({user:'visitor',canEdit:false,selected:[],toggle:()=>{}})
const useApp = () => useContext(AppContext)

function useApi<T>(path:string, enabled=true) {const {user}=useApp();return useQuery({queryKey:[user,path],queryFn:()=>api<T>(path,user),enabled})}
function ErrorBox({error}:{error:unknown}) {return error ? <div role="alert" className="error">{error instanceof Error ? error.message : 'Unable to load data. Check that the local API is running.'}</div> : null}
function Loading() {return <div className="loading" role="status"><LoaderCircle aria-hidden="true" size={22} className="spin"/> Loading local catalog…</div>}
function Status({value}:{value:string}) {return <span className={'status status-'+value.toLowerCase().replaceAll(' ','-')}>{value}</span>}
function PageTitle({eyebrow,title,description,action}:{eyebrow:string;title:string;description:string;action?:React.ReactNode}) {return <div className="page-title"><div><h1>{title}</h1><p>{description}</p></div>{action}</div>}
function SearchBox({initial=''}:{initial?:string}) {
 const [value,setValue]=useState(initial);const input=useRef<HTMLInputElement>(null);const navigate=useNavigate();const [params]=useSearchParams()
 return <form className="searchbox" role="search" onSubmit={e=>{e.preventDefault();const next=new URLSearchParams(params);next.delete('page');if(value.trim())next.set('q',value.trim());else next.delete('q');navigate('/catalog'+(next.size?'?'+next:''))}}><Search size={22} aria-hidden="true"/><input ref={input} aria-label="Search capabilities" maxLength={3000} placeholder="Describe a mission need, capability, or dataset…" value={value} onChange={e=>setValue(e.target.value)}/>{value&&<button type="button" className="catalog-clear" aria-label="Clear search" onClick={()=>{setValue('');input.current?.focus()}}><X aria-hidden="true" size={18}/></button>}<Button type="submit">Search </Button></form>
}

function ProjectCard({project:p,hit,compact=false}:{project:Project;hit?:Hit;compact?:boolean}) {
 const {selected,toggle}=useApp()
 return <article className={'project-card '+(compact?'compact':'')}>
  <div className="card-top"><span className="type-label"><Layers3 aria-hidden="true" size={15}/>{p.project_type}</span><Status value={p.status}/></div>
  <h3><Link to={'/projects/'+p.id}>{p.name}</Link></h3>
  <div className="organization">{p.organization}</div><p>{p.mission_problem}</p>
  {hit && <div className="evidence"><span><Sparkles aria-hidden="true" size={13}/> Match evidence, rank {hit.rank}</span><p>{hit.evidence[0]}</p><small>{hit.inference}</small></div>}
  <div className="tags"><span>{p.domain}</span>{p.technologies.slice(0,2).map(t=><span key={t}>{t}</span>)}</div>
  <div className="card-bottom"><Link to={'/projects/'+p.id}>View capability </Link><button className={'compare-toggle '+(selected.includes(p.id)?'chosen':'')} aria-label={'Compare '+p.name} aria-pressed={selected.includes(p.id)} onClick={()=>toggle(p.id)}><GitCompareArrows aria-hidden="true" size={15}/>{selected.includes(p.id)?'Selected':'Compare'}</button></div>
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
 const page=Math.max(1,Math.floor(Number(params.get('page'))||1)),pageSize=50
 const filters=['domain','project_type','organization','status'];const qs=new URLSearchParams();filters.forEach(key=>{const value=params.get(key);if(value)qs.set(key,value)});qs.set('limit',String(pageSize));qs.set('offset',String((page-1)*pageSize))
 const list=useApi<ProjectPage>('/projects/page?'+qs,!q)
 const results=useApi<SearchResult>('/search?'+params,!!q)
 function set(key:string,value:string) {const p=new URLSearchParams(params);p.delete('page');if(value)p.set(key,value);else p.delete(key);setParams(p)}
 const data=q?results.data?.results.map(h=>({project:h.project,hit:h})):list.data?.items.map(project=>({project,hit:undefined}))
 const pending=q?results.isPending:list.isPending
 return <><PageTitle eyebrow="THE SHARED CATALOG" title="Catalog" description="Search by mission, explore by domain, and follow the evidence." action={<Button asChild variant="outline"><Link to="/projects/new"><Plus size={16}/>Register project</Link></Button>}/><SearchBox key={q} initial={q}/>
 <div className="catalog-layout"><aside className="filters"><div className="section-title"><h2>Refine discovery</h2><button className="text-button" onClick={()=>setParams(q?{q}: {})}>Reset</button></div>{filters.map((key,i)=><label key={key}>{['Mission domain','Project type','Organization','Project status'][i]}<select value={params.get(key)||''} onChange={e=>set(key,e.target.value)}><option value="">All {['domains','types','organizations','statuses'][i]}</option>{[...new Set([...([domainQuery.data||[],types,orgQuery.data||[],statuses][i]),...(params.get(key)?[params.get(key)!]:[])])].map(x=><option key={x}>{x}</option>)}</select></label>)}<div className="filter-note"><ShieldCheck aria-hidden="true" size={19}/><p>Your identity determines which capabilities and contacts are discoverable.</p></div></aside>
 <section><div className="results-heading"><h2>{pending?'Searching…':`${q?results.data?.total??0:list.data?.total??0} ${q?'ranked matches':'capabilities'}`}{q&&results.data&&<small>, {results.data.elapsed_ms} ms</small>}</h2><label className="mode-label">Search mode<select value={mode} onChange={e=>set('mode',e.target.value)}>{searchModes.map(m=><option key={m} value={m}>{m[0].toUpperCase()+m.slice(1)}</option>)}</select></label></div><ErrorBox error={q?results.error:list.error}/>{pending?<Loading/>:data?.length?<div className="search-cards">{data.map(({project,hit})=><ProjectCard key={project.id} project={project} hit={hit}/>)}</div>:<div className="empty"><Search aria-hidden="true" size={32}/><h2>No capabilities found</h2><p>Try a broader mission description or clear a filter.</p></div>}{!q&&list.data&&list.data.total>pageSize&&<nav className="catalog-pagination" aria-label="Catalog pages"><Button variant="outline" disabled={page<=1} onClick={()=>set('page',String(page-1))}>Previous page</Button><span aria-live="polite">Page {page} of {Math.ceil(list.data.total/pageSize)}</span><Button variant="outline" disabled={page*pageSize>=list.data.total} onClick={()=>set('page',String(page+1))}>Next page</Button></nav>}{q&&results.data&&<p className="fine-print">Encoder: {results.data.encoder}. Ranking is a relative ordering, not a confidence percentage.</p>}</section></div></>
}

function ProjectDetail() {
 const {id}=useParams();const {user,canEdit,selected,toggle}=useApp();const navigate=useNavigate();const client=useQueryClient();const [confirm,setConfirm]=useState(false)
 const {data:p,error,isPending}=useApi<Project>('/projects/'+id)
 const relations=useApi<SearchResult>('/projects/'+id+'/related',!!p)
 const remove=useMutation({mutationFn:()=>api('/projects/'+id,user,{method:'DELETE'}),onSuccess:()=>{client.invalidateQueries();navigate('/catalog')}})
 if(isPending)return <Loading/>;if(!p)return <ErrorBox error={error}/>
 return <><Link className="back" to="/catalog"><ArrowLeft aria-hidden="true" size={16}/>Back to catalog</Link><PageTitle eyebrow={`${p.project_type.toUpperCase()}, SYNTHETIC RECORD`} title={p.name} description={p.organization} action={<div className="actions"><Button asChild variant="outline"><Link to={'/check?project='+p.id}><Workflow size={16}/>Check before you build</Link></Button><Button variant="outline" onClick={()=>toggle(p.id)}><GitCompareArrows size={16}/>{selected.includes(p.id)?'Remove comparison':'Add to comparison'}</Button>{canEdit&&<Button asChild><Link to={'/projects/'+p.id+'/edit'}>Edit project</Link></Button>}</div>}/>
 <div className="detail-layout"><div><section className="panel detail-panel"><div className="detail-meta"><Status value={p.status}/><span>{p.project_type}</span><span>{p.domain}</span><time dateTime={p.last_updated}>Updated {p.last_updated}</time></div><h2>Mission problem</h2><p className="mission-text">{p.mission_problem}</p><h2>About this capability</h2><p>{p.description}</p><h2>Technical approach</h2><p>{p.technical_summary||'Not provided.'}</p><div className="tags">{p.technologies.map(t=><span key={t}>{t}</span>)}</div><h2>Intended users</h2><p>{p.intended_users.join(', ')||'Unknown — not stated in the catalog.'}</p><h2>Stated use cases</h2><ul>{p.use_cases.map(t=><li key={t}>{t}</li>)}</ul><h2>Associated datasets</h2>{p.datasets.length?p.datasets.map(d=><div className="dataset-row" key={d.name}><Database aria-hidden="true" size={19}/><div><strong>{d.name}</strong><p>{d.description}</p></div></div>):<p>No datasets stated.</p>}</section>
 <ProjectMetadata project={p} user={user}/><section className="related-section"><div className="section-title"><div><h2>Related capabilities</h2></div></div><ErrorBox error={relations.error}/>{relations.isPending?<Loading/>:<div className="search-cards">{relations.data?.results.map(h=><ProjectCard key={h.project.id} project={h.project} hit={h}/>)}</div>}</section></div>
 <aside><section className="panel detail-panel"><h2><Users aria-hidden="true" size={18}/>Approved contacts</h2>{p.contacts.length?p.contacts.map(c=><div className="contact" key={c.method}><strong>{c.name}</strong><small>{c.role}</small><span>{c.method}</span></div>):<p>Approved POC information is unavailable for this view.</p>}{p.contacts_withheld&&<p className="fine-print">Some contact information is not available to this identity.</p>}<h2><BookOpen aria-hidden="true" size={18}/>Resources & access</h2>{[['Documentation',p.documentation_url],['Repository',p.repository_url],['Demonstration',p.demo_url]].map(([label,url])=>url&&<a className="resource" key={label} href={url} target="_blank" rel="noreferrer">{label}</a>)}<p className="fine-print">Reserved .example links identify fictional resources.</p><p>{p.access_instructions}</p><h2>Reuse considerations</h2>{[['License / terms',p.license],['Deployment',p.deployment],['Integration',p.integration]].map(([k,v])=><div className="reuse-field" key={k}><small>{k}</small><p>{v||'Unknown — confirm with the owner.'}</p></div>)}<div className="notice"><LockKeyhole aria-hidden="true" size={16}/><div><strong>{p.visibility} demo access</strong><p>{p.availability}. Application access label; not an official classification marking.</p></div></div></section>{canEdit&&<div className="delete-area"><Button variant="ghost" onClick={()=>confirm?remove.mutate():setConfirm(true)}>{remove.isPending?'Deleting…':confirm?'Confirm delete project':'Delete project'}</Button>{confirm&&<button className="text-button" onClick={()=>setConfirm(false)}>Cancel</button>}<ErrorBox error={remove.error}/></div>}</aside></div></>
}


function Compare() {
 const {selected,user}=useApp()
 const result=useQuery({queryKey:[user,'compare',selected],queryFn:()=>api<Comparison>('/projects/compare',user,{method:'POST',body:JSON.stringify({project_ids:selected})}),enabled:selected.length>=2})
 return <><PageTitle eyebrow="EVALUATE THE OVERLAP" title="Compare capabilities" description="A side-by-side view of stated metadata, differences, and questions to resolve."/>{selected.length<2?<div className="empty"><GitCompareArrows aria-hidden="true" size={32}/><h2>Select two or three capabilities</h2><p>Use Compare on any catalog card to add a project.</p><Button asChild><Link to="/catalog">Browse catalog</Link></Button></div>:result.isPending?<Loading/>:result.data?<><section className="panel"><ProjectComparison comparison={result.data}/></section></>:<ErrorBox error={result.error}/>}</>
}

function RegistryForm() {
 const {id}=useParams();const {canEdit,user}=useApp();const existing=useApi<Project>('/projects/'+id,!!id)
 if(!canEdit)return <><PageTitle eyebrow="PROJECT REGISTRY" title="Contribute to the shared picture" description="Select Catalog curator in the demo identity menu to register or edit projects."/><div className="notice"><LockKeyhole aria-hidden="true" size={20}/><p>Read access and edit permissions are enforced by the local API. Identity selection is a non-production demonstration.</p></div></>
 if(id&&existing.isPending)return <Loading/>
 if(id&&!existing.data)return <ErrorBox error={existing.error}/>
 return <RegistryEditor key={id||'new'} initial={existing.data} user={user}/>
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
     <Route path="/people" element={<RecordDirectory key="people" kind="people" user={user} canEdit={canEdit}/>}/>
     <Route path="/datasources" element={<RecordDirectory key="datasources" kind="datasources" user={user} canEdit={canEdit}/>}/>
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
   <CatalogChatBubble user={user}/>
   {selected.length>0&&<div className="comparison-tray"><GitCompareArrows aria-hidden="true" size={18}/><strong>{selected.length} of 3 selected</strong><Link to="/compare">Compare capabilities </Link><button aria-label="Clear comparison" onClick={()=>setSelected([])}><X aria-hidden="true" size={17}/></button></div>}
  </div>
 </AppContext.Provider>
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={queryClient}><BrowserRouter><App/></BrowserRouter></QueryClientProvider></React.StrictMode>)
