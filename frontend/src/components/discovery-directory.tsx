import {Link} from 'react-router-dom'
import {useQuery} from '@tanstack/react-query'
import {ArrowLeft, ArrowRight, Building2, Compass, LoaderCircle} from 'lucide-react'
import {api, type Overview} from '../api'
import {Button} from './button'

export function DiscoveryDirectory({kind,user}:{kind:'domains'|'organizations';user:string}) {
  const domains = kind==='domains'
  const overview = useQuery({queryKey:[user,'/analytics/overview'],queryFn:()=>api<Overview>('/analytics/overview',user),enabled:domains})
  const organizations = useQuery({queryKey:[user,'/organizations'],queryFn:()=>api<string[]>('/organizations',user),enabled:!domains})
  const query = domains?overview:organizations
  const names = domains?Object.keys(overview.data?.domains||{}).sort():organizations.data||[]
  const Icon = domains?Compass:Building2

  return <div className="discovery-directory">
    <Link className="back" to="/"><ArrowLeft size={16}/>Back to home</Link>
    <div className="page-title"><div><div className="eyebrow">EXPLORE THE SHARED CATALOG</div><h1>{domains?'Mission Domains':'Organizations'}</h1><p>{domains?'Discover capabilities by mission area.':'Connect with teams through their discoverable projects and approved contacts.'}</p></div></div>
    {query.isPending?<div className="loading" role="status"><LoaderCircle className="spin" size={22}/>Loading {domains?'mission domains':'organizations'}…</div>:query.isError?<div className="error" role="alert">Unable to load this directory. <Button variant="outline" onClick={()=>void query.refetch()}>Try again</Button></div>:names.length?<nav className="directory-grid" aria-label={domains?'Mission domains':'Organization directory'}>{names.map(name=><Link key={name} to={'/catalog?'+new URLSearchParams({[domains?'domain':'organization']:name})}><span className="directory-icon"><Icon size={23}/></span><div><h2>{name}</h2><p>{domains?`${overview.data!.domains[name]} ${overview.data!.domains[name]===1?'project':'projects'}`:'Explore team capabilities'}</p></div><ArrowRight size={18}/></Link>)}</nav>:<div className="empty"><Icon size={30}/><h2>No {domains?'mission domains':'organizations'} yet</h2><p>This catalog view has no projects to browse.</p></div>}
  </div>
}
