import {useState} from 'react'
import {useNavigate} from 'react-router-dom'
import {useMutation, useQueryClient} from '@tanstack/react-query'
import {Check, CircleHelp, Plus, Search} from 'lucide-react'
import {api, type Project} from '../api'
import {missionDomains, projectStatuses, projectTypes} from '../catalog-filters'
import {AutoTag} from './auto-tag'
import {Button} from './button'
import {ProjectMetadataFields} from './project-metadata'

const split=(text:string)=>text.split(',').map(value=>value.trim()).filter(Boolean)

export function RegistryEditor({initial,user}:{initial?:Project;user:string}) {
  const navigate=useNavigate()
  const client=useQueryClient()
  const [form,setForm]=useState<Record<string,string>>({
    name:initial?.name||'', description:initial?.description||'', mission_problem:initial?.mission_problem||'',
    project_type:initial?.project_type||'Application', domain:initial?.domain||'Maintenance', organization:initial?.organization||'',
    status:initial?.status||'Concept', technical_summary:initial?.technical_summary||'',
    technologies:initial?.technologies.join(', ')||'',
    datasets:initial?.datasets.map(dataset=>dataset.name+' | '+dataset.description).join('\n')||'',
    use_cases:initial?.use_cases.join('\n')||'', intended_users:initial?.intended_users.join(', ')||'',
    repository_url:initial?.repository_url||'', documentation_url:initial?.documentation_url||'', demo_url:initial?.demo_url||'',
    access_instructions:initial?.access_instructions||'', availability:initial?.availability||'Synthetic demonstration only',
    visibility:initial?.visibility||'public', allowed_groups:initial?.allowed_groups.join(', ')||'',
    license:initial?.license||'', deployment:initial?.deployment||'', integration:initial?.integration||'',
    classification:initial?.classification||'', network_accessibility:initial?.network_accessibility.join(',')||'',
    primary_poc_email:initial?.primary_poc_email||'', team_members:initial?.team_members.join(',')||'',
    sponsors:initial?.sponsors.join(', ')||'', project_url:initial?.project_url||'', datasource:initial?.datasource||'',
  })
  const [contacts,setContacts]=useState<Project['contacts']>(initial?.contacts||[])
  const [checked,setChecked]=useState(false)
  const [overlap,setOverlap]=useState<string[]|null>(null)
  const change=(key:string,value:string)=>{setForm(current=>({...current,[key]:value}));setChecked(false)}
  const mutation=useMutation({mutationFn:()=>{
    const payload:Record<string,unknown>={...form,
      technologies:split(form.technologies), intended_users:split(form.intended_users),
      allowed_groups:split(form.allowed_groups), use_cases:form.use_cases.split('\n').filter(Boolean), contacts,
      datasets:form.datasets.split('\n').filter(Boolean).map(value=>{const [name,...description]=value.split('|');return {name:name.trim(),description:description.join('|').trim()}}),
      repository_url:form.repository_url||null, documentation_url:form.documentation_url||null, demo_url:form.demo_url||null,
      license:form.license||null, deployment:form.deployment||null, integration:form.integration||null,
      classification:form.classification||null, network_accessibility:split(form.network_accessibility),
      primary_poc_email:form.primary_poc_email||null, team_members:split(form.team_members), sponsors:split(form.sponsors),
      project_url:form.project_url||null, datasource:form.datasource||null,
    }
    if(initial?.personnel_withheld){delete payload.primary_poc_email;delete payload.team_members}
    if(initial?.datasource_withheld)delete payload.datasource
    return api<Project>(initial?'/projects/'+initial.id:'/projects',user,{method:initial?'PATCH':'POST',body:JSON.stringify(payload)})
  },onSuccess:project=>{void client.invalidateQueries();navigate('/projects/'+project.id)}})
  const duplicate=useMutation({mutationFn:()=>api<{candidates:{project:Project}[]}>('/discovery/check-duplicate',user,{method:'POST',body:JSON.stringify({description:form.mission_problem+' '+form.description})}),onSuccess:data=>{setOverlap(data.candidates.filter(candidate=>candidate.project.id!==initial?.id).map(candidate=>candidate.project.name));setChecked(true)}})

  function field(key:string,label:string,options?:string[],multiline=false) {
    const required=['name','organization','description','mission_problem'].includes(key)
    return <label key={key}>{label}{options?<select value={form[key]} onChange={event=>change(key,event.target.value)}>{[...new Set([...options,form[key]])].filter(Boolean).map(value=><option key={value}>{value}</option>)}</select>:multiline?<textarea required={required} rows={3} value={form[key]} onChange={event=>change(key,event.target.value)}/>:<input required={required} type={key.endsWith('_url')?'url':'text'} value={form[key]} onChange={event=>change(key,event.target.value)}/>}</label>
  }
  const error=mutation.error||duplicate.error

  return <>
    <div className="page-title"><div><h1>{initial?'Edit project':'Register a project'}</h1><p>Use fictional, approved demonstration metadata only. All records are marked synthetic.</p></div></div>
    <form className="panel registry-form" onSubmit={event=>{event.preventDefault();if(!checked){duplicate.mutate();return}mutation.mutate()}}>
      <div className="form-grid">{field('name','Project name')}{field('organization','Fictional owning organization')}{field('project_type','Project type',projectTypes)}{field('domain','Mission domain',missionDomains)}{field('status','Project status',projectStatuses)}{field('visibility','Application access label',['public','internal','group'])}</div>
      {field('mission_problem','Mission problem',undefined,true)}{field('description','Description',undefined,true)}
      <AutoTag text={form.description+' '+form.mission_problem} user={user} onApply={suggestions=>{setChecked(false);setForm(current=>({...current,domain:suggestions.domain||current.domain,project_type:suggestions.project_type||current.project_type,technologies:suggestions.technologies.join(', '),datasets:suggestions.datasets.map(name=>name+' | ').join('\n')}))}}/>
      <ProjectMetadataFields user={user} initial={initial} form={form} onChange={change}/>
      {field('technical_summary','Technical approach',undefined,true)}
      <div className="form-grid">{field('intended_users','Intended users — comma separated')}{field('technologies','Technologies — comma separated')}{field('allowed_groups','Authorized demo groups — comma separated')}{field('availability','Availability / handling note')}</div>
      {field('datasets','Datasets — one per line: name | description',undefined,true)}{field('use_cases','Stated use cases — one per line',undefined,true)}
      <fieldset className="contacts-editor"><legend>Approved contacts</legend>{contacts.map((contact,index)=><div className="contact-editor form-grid" key={index}>{(['name','role','method'] as const).map(key=><label key={key}>{key==='method'?'Approved contact method':key==='name'?'Fictional contact name':'Contact role'}<input required value={contact[key]} onChange={event=>setContacts(contacts.map((item,i)=>i===index?{...item,[key]:event.target.value}:item))}/></label>)}<label>Contact visibility<select value={contact.visibility} onChange={event=>setContacts(contacts.map((item,i)=>i===index?{...item,visibility:event.target.value}:item))}>{['public','internal','group'].map(value=><option key={value}>{value}</option>)}</select></label><Button type="button" variant="ghost" onClick={()=>setContacts(contacts.filter((_,i)=>i!==index))}>Remove contact</Button></div>)}<Button type="button" variant="outline" onClick={()=>setContacts([...contacts,{name:'',role:'Project liaison',method:'',visibility:'public'}])}><Plus aria-hidden="true" size={15}/>Add approved contact</Button></fieldset>
      <div className="form-grid">{field('repository_url','Repository URL')}{field('documentation_url','Documentation URL')}{field('demo_url','Demonstration URL')}{field('license','License / reuse terms')}{field('deployment','Deployment information')}{field('integration','Integration compatibility')}</div>
      {field('access_instructions','Access request instructions',undefined,true)}
      {overlap&&<div className="notice"><CircleHelp aria-hidden="true" size={20}/><p>Check before you build found these leads: {overlap.join(', ')||'No evidence-backed matches'}. Review the catalog before proceeding; duplication is a human determination.</p></div>}
      {error&&<div role="alert" className="error">{error instanceof Error?error.message:'Unable to save this project.'}</div>}
      <div className="actions"><Button disabled={mutation.isPending||duplicate.isPending} type="submit">{checked?<><Check aria-hidden="true" size={17}/>Save project</>:<><Search aria-hidden="true" size={17}/>Check for existing capabilities</>}</Button><Button variant="ghost" type="button" onClick={()=>navigate('/catalog')}>Cancel</Button></div>
    </form>
  </>
}
