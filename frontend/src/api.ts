export type Person = {email:string; full_name:string; organization:string; job_title:string; work_phone:string|null; areas_of_expertise:string[]; visibility:string; allowed_groups:string[]}
export type Datasource = {name:string; description:string; domain:string; organization:string; visibility:string; allowed_groups:string[]}
export type Project = {id:string; name:string; description:string; mission_problem:string; project_type:string; domain:string; organization:string; status:string; technical_summary:string; contacts:{name:string;role:string;method:string;visibility:string}[]; contacts_withheld:boolean; repository_url:string|null; documentation_url:string|null; demo_url:string|null; access_instructions:string; availability:string; visibility:string; allowed_groups:string[]; technologies:string[]; datasets:{name:string;description:string}[]; use_cases:string[]; intended_users:string[]; last_updated:string; license:string|null; deployment:string|null; integration:string|null; synthetic:boolean; classification:string|null; network_accessibility:string[]; primary_poc_email:string|null; team_members:string[]; personnel_withheld:boolean; sponsors:string[]; project_url:string|null; datasource:string|null; datasource_withheld:boolean; date_created:string|null}
export type ProjectPage = {total:number;items:Project[]}
export type Hit = {project:Project;rank:number;ranking_score:number;evidence:string[];inference:string}
export type SearchResult = {query:string;mode:string;encoder:string;total:number;elapsed_ms:number;results:Hit[]}
export type Overview = {total:number;domains:Record<string,number>;statuses:Record<string,number>;recent:Project[];collaborators:Project[]}
export type Citation = {project_id:string;project_name:string;url:string;field:string;value:unknown}
export type Constraint = {dimension:string;state:'unknown'|'requires_confirmation'|'potential_mismatch'|'blocking';detail:string;question:string;citation:Citation}
export type Activity = {step:number;tool:string;detail:string;project_ids:string[];status:'running'|'complete'|'failed';started_at:string;finished_at:string|null;elapsed_ms:number}
export type Candidate = {project:Project;classification:string;evidence:string[];inference:string;recommendation:string;open_questions:string[];citations:Citation[];constraints:Constraint[];rank:number;relationship:string;similarity_components:{matching_concepts:string[];matching_mission_terms:string[];shared_datasets:string[];shared_technologies:string[];shared_intended_users:string[];same_domain:boolean|null;relative_score:number;notice:string};differences:string[];origins:{kind:'hybrid'|'related';via_project_id:string|null}[]}
export type Assessment = {concepts:string[];candidates:Candidate[];decision_notice:string}
export type Comparison = {projects:Project[];shared_datasets:string[];potential_overlap:string;differences:string[];open_questions:string[];shared_technologies:string[];shared_intended_users:string[];similarities:string[];collaboration_opportunities:string[]}
export type Proposal = {proposed_name:string;mission_problem:string;description:string;intended_solution:string;domain:string|null;datasets:string[];technologies:string[];intended_users:string[];desired_capabilities:string[]}
export type AgentRun = {id:string;timeline:Activity[];assessment:Assessment;comparison:Comparison|null;proposal:Proposal;encoder:string;workflow_version:number;recommendation:{decision:string;summary:string;citations:Citation[];actions:{action:string;reason:string;citations:Citation[]}[];gaps:string[]};experts:{project_id:string;project_name:string;contacts:Project['contacts']}[];access:{project_id:string;instructions:string;documentation_url:string|null;contacts:Project['contacts']}[]}

export type DiscoveryEvent = {type:'run';run_id:string}|{type:'activity';activity:Activity}|{type:'result';run:AgentRun}|{type:'error';message:string}

export async function streamDiscovery(proposal:Proposal,user:string,onEvent:(event:DiscoveryEvent)=>void,signal:AbortSignal):Promise<AgentRun> {
  const response=await fetch('/api/v1/agent/discover/stream',{method:'POST',headers:{'Content-Type':'application/json','X-Demo-User':user},body:JSON.stringify(proposal),signal})
  if(!response.ok) {const body=await response.json();throw new Error(typeof body.detail==='string'?body.detail:JSON.stringify(body.detail))}
  if(!response.body)throw new Error('Discovery streaming is unavailable.')
  const reader=response.body.getReader(),decoder=new TextDecoder()
  let buffer='',result:AgentRun|undefined
  function consume(line:string) {if(!line.trim())return;const event=JSON.parse(line) as DiscoveryEvent;onEvent(event);if(event.type==='error')throw new Error(event.message);if(event.type==='result')result=event.run}
  try {
    while(true) {const {done,value}=await reader.read();buffer+=decoder.decode(value,{stream:!done});let index:number;while((index=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,index));buffer=buffer.slice(index+1)}if(done)break}
    if(buffer.trim())consume(buffer)
    if(!result)throw new Error('Discovery ended before a grounded recommendation was completed.')
    return result
  } finally {reader.releaseLock()}
}

export async function api<T>(path:string, user:string, init?:RequestInit):Promise<T> {
  const response = await fetch('/api/v1'+path, {...init, headers:{'Content-Type':'application/json','X-Demo-User':user,...init?.headers}})
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try { const body = await response.json(); message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail) } catch { /* retain HTTP status */ }
    throw new Error(message)
  }
  return response.status === 204 ? undefined as T : response.json()
}
