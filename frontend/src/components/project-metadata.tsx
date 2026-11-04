import {useQuery} from '@tanstack/react-query'
import {Link} from 'react-router-dom'
import {ArrowUpRight, RefreshCw} from 'lucide-react'
import {api, type Datasource, type Person, type Project} from '../api'
import {networks} from '../catalog-filters'
import {Button} from './button'

type MetadataProps = {user:string; initial?:Project; form:Record<string,string>; onChange:(key:string,value:string)=>void}

export function ProjectMetadataFields({user,initial,form,onChange}:MetadataProps) {
  const people=useQuery({queryKey:[user,'/people'],queryFn:()=>api<Person[]>('/people',user)})
  const sources=useQuery({queryKey:[user,'/datasources'],queryFn:()=>api<Datasource[]>('/datasources',user)})
  const selectedNetworks=form.network_accessibility.split(',').filter(Boolean)
  const members=form.team_members.split(',').filter(Boolean)
  const required=!initial
  return <fieldset className="metadata-fields">
    <legend>Project catalog fields</legend>
    <div className="metadata-help"><p>Manage <Link to="/people" target="_blank" rel="noreferrer">personnel</Link> and <Link to="/datasources" target="_blank" rel="noreferrer">datasources</Link> in a separate tab, then refresh these choices.</p><Button type="button" variant="outline" onClick={()=>{void people.refetch();void sources.refetch()}}><RefreshCw size={14}/>Refresh choices</Button></div>
    {(people.isError||sources.isError)&&<p className="error" role="alert">Some registry choices could not be loaded. Use Refresh choices to retry.</p>}
    <div className="form-grid">
      <label>Classification{required&&<small> required</small>}<input required={required||!!initial?.classification} maxLength={100} value={form.classification} placeholder="Enter the recorded classification" onChange={e=>onChange('classification',e.target.value)}/><small>Catalog metadata; application visibility is configured separately.</small></label>
      <label>Team lead / primary POC{required&&<small> required</small>}<select required={required||!!initial?.primary_poc_email} disabled={initial?.personnel_withheld} value={form.primary_poc_email} onChange={e=>onChange('primary_poc_email',e.target.value)}><option value="">{people.isPending?'Loading personnel…':initial?.personnel_withheld?'Reference unavailable in this view':'Select a registered person'}</option>{people.data?.map(person=><option key={person.email} value={person.email}>{person.full_name} · {person.email}</option>)}</select></label>
      <label>Sponsors <small>comma separated · optional</small><input value={form.sponsors} maxLength={6000} onChange={e=>onChange('sponsors',e.target.value)}/></label>
      <label>Datasource <small>optional</small><select disabled={initial?.datasource_withheld} value={form.datasource} onChange={e=>onChange('datasource',e.target.value)}><option value="">{sources.isPending?'Loading datasources…':initial?.datasource_withheld?'Reference unavailable in this view':'No datasource selected'}</option>{sources.data?.map(source=><option key={source.name}>{source.name}</option>)}</select></label>
      <label>Project URL <small>optional</small><input type="url" value={form.project_url} onChange={e=>onChange('project_url',e.target.value)}/></label>
      <div className="metadata-dates"><span>Project ID</span><p>{initial?.id||'Assigned when saved'}</p><span>Date created</span><p>{initial?.date_created|| (initial?'Unknown — not recorded':'Assigned when saved')}</p><span>Last updated</span><p>{initial?.last_updated||'Assigned when saved'}</p></div>
    </div>
    <fieldset className="metadata-options"><legend>Network accessibility{required?' · choose at least one':''}</legend><div>{networks.map((network,index)=><label key={network}><input type="checkbox" required={(required||!!initial?.network_accessibility.length)&&selectedNetworks.length===0&&index===0} checked={selectedNetworks.includes(network)} onChange={e=>onChange('network_accessibility',(e.target.checked?[...selectedNetworks,network]:selectedNetworks.filter(value=>value!==network)).join(','))}/>{network}</label>)}</div></fieldset>
    <fieldset className="metadata-options" disabled={initial?.personnel_withheld}><legend>Team members · optional</legend>{people.data?.length?<div>{people.data.map(person=><label key={person.email}><input type="checkbox" checked={members.includes(person.email)} onChange={e=>onChange('team_members',(e.target.checked?[...members,person.email]:members.filter(value=>value!==person.email)).join(','))}/><span>{person.full_name}<small>{person.email}</small></span></label>)}</div>:<p>{people.isPending?'Loading personnel…':'No personnel available. Add a person in the personnel registry.'}</p>}</fieldset>
    {initial?.personnel_withheld&&<p className="fine-print">Unavailable personnel references are preserved when you save other project changes.</p>}
  </fieldset>
}

export function ProjectMetadata({project:p,user}:{project:Project;user:string}) {
  const people=useQuery({queryKey:[user,'/people'],queryFn:()=>api<Person[]>('/people',user),enabled:!!p.primary_poc_email||p.team_members.length>0})
  const emails=[...new Set([p.primary_poc_email,...p.team_members].filter((email):email is string=>!!email))]
  return <section className="panel project-metadata">
    <h2>Catalog metadata</h2><dl className="metadata-definitions">{[
      ['Project ID',p.id],['Classification',p.classification],['Network accessibility',p.network_accessibility.join(', ')],['Sponsors',p.sponsors.join(', ')],['Date created',p.date_created],['Last updated',p.last_updated],
    ].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value||'Unknown — not recorded'}</dd></div>)}</dl>
    {p.project_url&&<a className="resource" href={p.project_url} target="_blank" rel="noreferrer">Project location<ArrowUpRight size={16}/></a>}
    <h2>Project team</h2>{emails.length?<div>{emails.map(email=>{const person=people.data?.find(person=>person.email===email);return <div className="metadata-team-member" key={email}><strong>{person?.full_name||email}{email===p.primary_poc_email&&<span>Primary POC</span>}</strong><p>{email}</p>{person&&<p>{person.job_title} · {person.organization}</p>}</div>})}</div>:<p>No personnel references are available in this catalog view.</p>}
    {p.personnel_withheld&&<p className="fine-print">Some personnel references are unavailable to this identity.</p>}
    {people.isError&&<p className="fine-print" role="alert">Personnel details could not be loaded. <button className="text-button" onClick={()=>void people.refetch()}>Try again</button></p>}
    <h2>Datasource</h2>{p.datasource?<Link className="metadata-source" to={'/datasources?q='+encodeURIComponent(p.datasource)}>{p.datasource}<ArrowUpRight size={15}/></Link>:<p>{p.datasource_withheld?'Datasource reference is unavailable in this view.':'No datasource selected.'}</p>}
  </section>
}
