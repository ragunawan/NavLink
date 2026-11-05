import {useEffect, useRef, useState} from 'react'
import {Link, useSearchParams} from 'react-router-dom'
import {useQuery, useQueryClient} from '@tanstack/react-query'
import {CheckCircle2, CircleHelp, GitCompareArrows, LoaderCircle, ShieldCheck, Sparkles, Users, Workflow} from 'lucide-react'
import {api, streamDiscovery, type Activity, type AgentRun, type Citation, type Comparison, type Project, type Proposal} from './api'
import {AutoTag} from './components/auto-tag'
import {Button} from './components/button'
import {ProjectComparison} from './components/project-comparison'

const domains=['Financial management','Logistics','Readiness','Maintenance','Personnel','Acquisition','Cybersecurity','Other']
const maintenance='We plan to build an AI-powered predictive maintenance system that analyzes historical equipment failures and supply data to forecast maintenance needs.'
const financial='Build a financial dashboard to track budget execution, obligations and expenditures across funding lines.'
const terms=(s:string)=>s.split(',').map(x=>x.trim()).filter(Boolean)

function SourceLinks({citations}:{citations:Citation[]}) {
  const projects=[...new Map(citations.map(c=>[c.project_id,c])).values()]
  return <span className="source-links">{projects.map(c=><Link key={c.project_id} to={c.url} title={'Catalog fields: '+citations.filter(x=>x.project_id===c.project_id).map(x=>x.field.replaceAll('_',' ')).join(', ')}>{c.project_name}</Link>)}</span>
}

function valueLabel(value:unknown):string {
  if(value==null||value==='')return 'Not stated in this catalog record.'
  if(Array.isArray(value))return value.length?value.map(x=>typeof x==='string'?x:typeof x==='object'&&x!==null?('name' in x?String(x.name):'Catalog metadata'):String(x)).join(', '):'None listed in this view.'
  return String(value)
}

function Evidence({citations}:{citations:Citation[]}) {
  return <div className="field-evidence">{citations.map(c=><div key={c.project_id+c.field}><Link to={c.url}><span>{c.field.replaceAll('_',' ')}</span></Link><p>{valueLabel(c.value)}</p></div>)}</div>
}

function Timeline({activities,pending}:{activities:Activity[];pending:boolean}) {
  return <div className="execution-log" aria-live="polite" aria-label="Agent execution timeline">
    <div className="execution-status">{pending?<LoaderCircle aria-hidden="true" size={16} className="spin"/>:<CheckCircle2 aria-hidden="true" size={16}/>}<strong>{pending?'Inspecting the local catalog':'Execution finished'}</strong><span>{activities.filter(a=>a.status==='complete').length} steps completed</span></div>
    <ol className="timeline">{activities.map(t=><li key={t.step} data-status={t.status}>{t.status==='running'?<LoaderCircle aria-hidden="true" size={17} className="spin"/>:t.status==='failed'?<CircleHelp aria-hidden="true" size={17}/>:<CheckCircle2 aria-hidden="true" size={17}/>}<div><strong>{t.tool.replaceAll('_',' ')}</strong><p>{t.detail}</p><small>{new Date(t.started_at).toLocaleTimeString()}, {t.status==='running'?'Running':t.status==='failed'?'Failed':`${t.elapsed_ms.toFixed(1)} ms`}</small><div className="timeline-links">{t.project_ids.slice(0,4).map(id=><Link key={id} to={'/projects/'+id}>{id}</Link>)}</div></div></li>)}</ol>
  </div>
}

function InlineComparison({run,user}:{run:AgentRun;user:string}) {
  const projects=run.assessment.candidates.map(c=>c.project)
  const [ids,setIds]=useState(run.comparison?.projects.map(p=>p.id)||projects.slice(0,2).map(p=>p.id))
  const comparison=useQuery({queryKey:[user,'advisor-comparison',ids],queryFn:()=>api<Comparison>('/projects/compare',user,{method:'POST',body:JSON.stringify({project_ids:ids})}),enabled:ids.length===2&&ids[0]!==ids[1]})
  if(projects.length<2)return null
  return <section className="panel inline-comparison" aria-label="Compare assessed projects"><div className="section-title"><div><h2><GitCompareArrows aria-hidden="true" size={20}/> Compare assessed projects</h2></div></div><div className="comparison-selectors">{[0,1].map(index=><label key={index}>Comparison project {index+1}<select aria-label={'Comparison project '+(index+1)} value={ids[index]||''} onChange={e=>setIds(ids.map((id,i)=>i===index?e.target.value:id))}>{projects.map(p=><option key={p.id} value={p.id} disabled={p.id===ids[1-index]}>{p.name}</option>)}</select></label>)}</div>{comparison.isPending?<p role="status">Loading comparison…</p>:comparison.error?<div className="error" role="alert">{comparison.error.message}</div>:comparison.data&&<ProjectComparison comparison={comparison.data}/>}</section>
}

export function CheckBeforeBuild({user}:{user:string}) {
  const [params,setParams]=useSearchParams(),client=useQueryClient()
  const savedId=params.get('run'), projectId=params.get('project')
  const sourceProject=useQuery({queryKey:[user,'proposal-source',projectId],queryFn:()=>api<Project>('/projects/'+projectId,user),enabled:!!projectId,retry:false})
  const saved=useQuery({queryKey:[user,'advisor-run',savedId],queryFn:()=>api<AgentRun>('/agent/runs/'+savedId,user),enabled:!!savedId,retry:false})
  const [description,setDescription]=useState(''),[solution,setSolution]=useState(''),[domain,setDomain]=useState(''),[datasets,setDatasets]=useState(''),[tech,setTech]=useState('')
  const [name,setName]=useState(''),[projectDescription,setProjectDescription]=useState(''),[intendedUsers,setIntendedUsers]=useState(''),[capabilities,setCapabilities]=useState(''),[expanded,setExpanded]=useState(false)
  const [result,setResult]=useState<AgentRun>(),[activities,setActivities]=useState<Activity[]>([]),[pending,setPending]=useState(false),[error,setError]=useState('')
  const controller=useRef<AbortController|null>(null),hydrated=useRef<string|null>(null)
  const run=result||saved.data
  useEffect(()=>()=>controller.current?.abort(),[])
  useEffect(()=>{if(sourceProject.data&&hydrated.current!=='project:'+sourceProject.data.id){const p=sourceProject.data;setDescription(p.mission_problem);setProjectDescription(p.description);setName(p.name);setDomain(p.domain);setSolution(p.project_type);setDatasets(p.datasets.map(d=>d.name).join(', '));setTech(p.technologies.join(', '));setIntendedUsers(p.intended_users.join(', '));hydrated.current='project:'+p.id}},[sourceProject.data])
  useEffect(()=>{if(saved.data&&hydrated.current!==saved.data.id){const p=saved.data.proposal;setDescription(p.mission_problem||p.description);setProjectDescription(p.mission_problem?p.description:'');setName(p.proposed_name||'');setIntendedUsers((p.intended_users||[]).join(', '));setCapabilities((p.desired_capabilities||[]).join(', '));setSolution(p.intended_solution);setDomain(p.domain||'');setDatasets(p.datasets.join(', '));setTech(p.technologies.join(', '));hydrated.current=saved.data.id}},[saved.data])
  function edited() {setExpanded(false);setResult(undefined);setActivities([]);setError('');if(savedId)setParams({},{replace:true})}
  function loadExample(finance:boolean) {edited();setDescription(finance?financial:maintenance);setDomain(finance?'Financial management':'Maintenance');setDatasets(finance?'Budget execution ledger, Obligation transactions':'Equipment failure history, Maintenance work orders, Supply inventory');setSolution('');setTech('');setName('');setProjectDescription('');setIntendedUsers('');setCapabilities('')}
  async function start() {
    controller.current?.abort();const active=new AbortController();controller.current=active
    setPending(true);setError('');setResult(undefined);setActivities([]);setParams({},{replace:true})
    const proposal:Proposal={proposed_name:name,mission_problem:description,description:projectDescription,intended_users:terms(intendedUsers),desired_capabilities:terms(capabilities),intended_solution:solution,domain:domain||null,datasets:terms(datasets),technologies:terms(tech)}
    try {
      const completed=await streamDiscovery(proposal,user,event=>{if(event.type==='activity')setActivities(previous=>[...previous.filter(a=>a.step!==event.activity.step),event.activity].sort((a,b)=>a.step-b.step))},active.signal)
      if(active.signal.aborted)return
      setResult(completed);client.setQueryData([user,'advisor-run',completed.id],completed);setParams({run:completed.id},{replace:true})
    } catch(e) {if(!active.signal.aborted)setError(e instanceof Error?e.message:'Discovery failed. Check the local API.')}
    finally {if(!active.signal.aborted)setPending(false)}
  }
  return <>
    <div className="page-title"><div><h1>Check before you build</h1><p>Turn a mission need into evidence-backed leads for reuse and collaboration.</p></div></div>
    <div className="check-layout"><section className="panel proposal-panel"><div className="section-title"><h2><Workflow aria-hidden="true" size={21}/> Describe your idea</h2></div>
      <form onSubmit={e=>{e.preventDefault();void start()}}><fieldset className="proposal-fields" disabled={pending}><label>Proposed project name <small>optional</small><input maxLength={160} value={name} onChange={e=>{edited();setName(e.target.value)}}/></label><label>What mission problem are you solving?<textarea minLength={15} maxLength={5000} rows={6} placeholder="I want to build a platform that…" value={description} onChange={e=>{edited();setDescription(e.target.value)}}/></label>
        <label>Project description <small>mission problem or description required</small><textarea minLength={15} maxLength={5000} rows={3} value={projectDescription} onChange={e=>{edited();setProjectDescription(e.target.value)}}/></label><div className="example-buttons"><span>Load an example</span><button type="button" onClick={()=>loadExample(false)}>Predictive maintenance</button><button type="button" onClick={()=>loadExample(true)}>Financial management</button></div>
        <AutoTag text={[description,projectDescription].filter(Boolean).join(' ')} user={user} onApply={suggestions=>{edited();if(suggestions.project_type)setSolution(suggestions.project_type);if(suggestions.domain)setDomain(suggestions.domain);if(suggestions.datasets.length)setDatasets(suggestions.datasets.join(', '));if(suggestions.technologies.length)setTech(suggestions.technologies.join(', '))}}/><label>Intended solution <small>optional</small><input maxLength={2000} value={solution} onChange={e=>{edited();setSolution(e.target.value)}} placeholder="A dashboard, model, dataset, or workflow"/></label>
        <label>Mission domain<select value={domain} onChange={e=>{edited();setDomain(e.target.value)}}><option value="">Infer from mission need</option>{[...domains,...(domain&&!domains.includes(domain)?[domain]:[])].map(d=><option key={d}>{d}</option>)}</select></label>
        <label>Datasets <small>comma separated, optional</small><input value={datasets} onChange={e=>{edited();setDatasets(e.target.value)}} placeholder="Maintenance work orders, Supply inventory"/></label>
        <label>Intended users <small>comma separated, optional</small><input value={intendedUsers} onChange={e=>{edited();setIntendedUsers(e.target.value)}} placeholder="Maintenance planners, equipment analysts"/></label><label>Desired capabilities <small>comma separated, optional</small><input value={capabilities} onChange={e=>{edited();setCapabilities(e.target.value)}} placeholder="Failure forecasting, readiness reporting"/></label><label>Technology stack <small>comma separated, optional</small><input value={tech} onChange={e=>{edited();setTech(e.target.value)}} placeholder="Python, React, SQLite"/></label>
        <Button disabled={pending} type="submit">{pending?<LoaderCircle aria-hidden="true" className="spin" size={17}/>:<Sparkles aria-hidden="true" size={17}/>}Analyze Proposal </Button>
      </fieldset></form>
      {(error||saved.error||sourceProject.error)&&<div className="error" role="alert">{error||saved.error?.message||sourceProject.error?.message}</div>}
      <p className="fine-print">Runs local hybrid retrieval, record inspection and deterministic evidence assessment. No LLM credentials or internet connection required.</p>
    </section>
    <aside className="panel workflow-panel"><h2>From idea to informed decision.</h2><p>Follow the actual operations as they run. Each recommendation links to the catalog metadata that supports it.</p>
      {activities.length||run?<Timeline activities={activities.length?activities:run!.timeline} pending={pending}/>:<ol className="workflow-steps">{['Interpret mission concepts','Run hybrid search and follow related entries','Inspect records and compare mission evidence','Evaluate access and reuse constraints','Recommend cited leads for your review'].map((t,i)=><li key={t}><span>{i+1}</span>{t}</li>)}</ol>}
      <div className="notice"><ShieldCheck aria-hidden="true" size={19}/><p>Similarity is a starting point. The advisor never grants access or declares a capability reusable.</p></div>
    </aside></div>
    {saved.isFetching&&!run&&<p role="status" className="loading">Loading saved assessment…</p>}
    {run&&<section className="assessment"><div className="section-title"><div><h2>Discovery assessment</h2></div><span className="local-pill"><CheckCircle2 aria-hidden="true" size={15}/>Workflow complete</span></div>
      <section className="panel recommendation-summary" aria-label="Grounded recommendation"><h2>Recommended path</h2><p>{run.recommendation.summary}</p><SourceLinks citations={run.recommendation.citations}/>
        <ol className="recommendation-actions">{run.recommendation.actions.map((action,i)=><li key={i}><strong>{action.action}</strong><p>{action.reason}</p><SourceLinks citations={action.citations}/></li>)}</ol>
        <details><summary>Coverage and unresolved questions</summary><ul>{run.recommendation.gaps.map(gap=><li key={gap}>{gap}</li>)}</ul></details>
      </section>
      <div className="tags">{run.assessment.concepts.map(c=><span key={c}>{c}</span>)}</div><p className="assessment-notice">{run.assessment.decision_notice}</p>
      <section className="panel collaboration-section" aria-label="Collaboration opportunities"><div className="section-title"><h2><Users aria-hidden="true" size={20}/> Collaboration opportunities</h2></div>{[...run.assessment.candidates].sort((a,b)=>Number(b.project.status==='Seeking Collaborators')-Number(a.project.status==='Seeking Collaborators')).slice(0,5).map(c=><article className="collaboration-row" key={c.project.id}><div><Link to={'/projects/'+c.project.id}><strong>{c.project.name}</strong></Link><p>{c.project.organization}, {c.project.domain}, {c.project.status}</p><p>{c.recommendation}</p><small>{c.project.contacts.length?c.project.contacts.map(contact=>contact.name+', '+contact.method).join('; '):'Approved contact unavailable.'}</small><details><summary>Access and compatibility questions</summary><ul>{c.open_questions.map(q=><li key={q}>{q}</li>)}</ul></details></div></article>)}{!run.assessment.candidates.length&&<p>No evidence-backed collaboration leads in this assessment.</p>}</section><InlineComparison key={run.id} run={run} user={user}/>
      {!run.assessment.candidates.length?<div className="empty"><CircleHelp aria-hidden="true" size={30}/><h2>No evidence-backed overlap identified</h2><p>Absence of matches does not prove that no similar project exists. Refine the proposal or broaden the catalog.</p></div>:<div className="assessment-grid">{(expanded?run.assessment.candidates:run.assessment.candidates.slice(0,5)).map(c=><article className="panel candidate" key={c.project.id}>
        <div className={'classification '+(c.classification==='Potential duplicate'?'duplicate':'')}>{c.classification}</div><h3><Link to={'/projects/'+c.project.id}>{c.project.name}</Link></h3><span className="status">{c.project.status}</span>
        <p className="organization">{c.project.organization}, {c.project.domain}</p><span className="relationship-label">{c.relationship}, rank {c.rank}</span><small className="retrieval-origin">{c.origins.some(o=>o.kind==='hybrid')?(c.origins.some(o=>o.kind==='related')?'Inspected through hybrid search and related-project connections':'Inspected from hybrid retrieval'):'Discovered through related-project connections and inspected'}</small>
        <h4>Catalog evidence, cited fields</h4><Evidence citations={c.citations}/><details><summary>How this was inferred</summary><p>{c.inference}</p></details>
        <details><summary>Similarity components and key differences</summary><p>Matched concepts: {c.similarity_components.matching_concepts.join(', ')||'None recognized'}</p><p>Shared datasets: {c.similarity_components.shared_datasets.join(', ')||'None stated'}</p><p>Shared technology: {c.similarity_components.shared_technologies.join(', ')||'None stated'}</p><p>Shared intended users: {c.similarity_components.shared_intended_users.join(', ')||'Unknown or no exact match'}</p><ul>{c.differences.map(d=><li key={d}>{d}</li>)}</ul><p>{c.similarity_components.notice}</p></details><h4>Suggested next step</h4><p>{c.recommendation}</p>
        <details className="reuse-constraints"><summary>Reuse constraints ({c.constraints.length})</summary>{c.constraints.map(constraint=><div className="constraint" key={constraint.dimension}><div><strong>{constraint.dimension}</strong><span className={'constraint-state '+constraint.state}>{constraint.state.replaceAll('_',' ')}</span></div><p>{constraint.detail}</p><p>{constraint.question}</p><SourceLinks citations={[constraint.citation]}/></div>)}</details>
        <div className="candidate-contact">{c.project.contacts.length?<><Users aria-hidden="true" size={15}/>{c.project.contacts[0].name}, {c.project.contacts[0].method}</>:<>Approved contact unavailable; see the owning organization.</>}</div>
        <Button asChild variant="outline"><Link to={'/projects/'+c.project.id}>Review supporting record </Link></Button>
      </article>)}</div>}
      {run.assessment.candidates.length>5&&<Button variant="outline" onClick={()=>setExpanded(!expanded)}>{expanded?'Show top 5':'Show all '+run.assessment.candidates.length+' assessed projects'}</Button>}<p className="fine-print">Deterministic assessment, generated without an LLM.</p><p className="fine-print">Run {run.id}, {run.encoder}, Saved locally; reload this page to reopen the evidence. Catalog or access changes invalidate saved assessments.</p>
    </section>}
  </>
}
