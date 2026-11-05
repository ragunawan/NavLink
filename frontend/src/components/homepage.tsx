import {useRef, useState, type ReactNode} from 'react'
import {Link, useNavigate} from 'react-router-dom'
import {useQuery} from '@tanstack/react-query'
import {ChevronDown, FolderOpen, LoaderCircle, Search, ShieldCheck, SlidersHorizontal, Workflow, X} from 'lucide-react'
import {api, type Overview, type Project} from '../api'
import {projectStatuses, projectTypes, searchModes, searchModeLabel} from '../catalog-filters'
import {Button} from './button'

const suggestions = ['Find similar analytics projects', 'Who is working on machine learning?', 'Existing logistics dashboards', 'Find Navy automation tools']
const emptyFilters = {project_type:'', domain:'', organization:'', status:''}

function HomeSearch({domains, organizations, loading, error}:{domains:string[]; organizations:string[]; loading:boolean; error:unknown}) {
  const navigate = useNavigate()
  const input = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('hybrid')
  const [expanded, setExpanded] = useState(false)
  const [filters, setFilters] = useState(emptyFilters)
  const filterCount = Object.values(filters).filter(Boolean).length

  function search(value=query) {
    const params = new URLSearchParams()
    if(value.trim()) params.set('q', value.trim())
    if(mode!=='hybrid') params.set('mode', mode)
    Object.entries(filters).forEach(([key,value])=>{if(value) params.set(key,value)})
    navigate('/catalog'+(params.size?'?'+params.toString():''))
  }

  return <div className="home-search-area">
    <form onSubmit={e=>{e.preventDefault();search()}} role="search" aria-label="Discover Navy capabilities">
      <label className="home-search-label" htmlFor="home-query">Search the catalog</label>
      <div className="home-searchbar">
        <Search size={23} aria-hidden="true"/>
        <input id="home-query" ref={input} aria-label="Search capabilities" maxLength={3000} placeholder="Hello, what are you looking for?" value={query} onChange={e=>setQuery(e.target.value)}/>
        {query&&<button className="home-clear" type="button" aria-label="Clear search" onClick={()=>{setQuery('');input.current?.focus()}}><X aria-hidden="true" size={18}/></button>}
        <button className={'home-filter-toggle'+(expanded?' is-active':'')} type="button" aria-expanded={expanded} aria-controls="home-filters" onClick={()=>setExpanded(!expanded)}>
          <SlidersHorizontal size={18} aria-hidden="true"/><span>Filters</span>{filterCount>0&&<b>{filterCount}</b>}<ChevronDown size={14} aria-hidden="true"/>
        </button>
        <Button type="submit">Search</Button>
      </div>
      <label className="home-search-mode">Search mode<select className={mode==='openai'?'si-powered':''} value={mode} onChange={e=>setMode(e.target.value)}>{searchModes.map(value=><option key={value} value={value}>{searchModeLabel(value)}</option>)}</select></label>
      {expanded&&<fieldset id="home-filters" className="home-filter-panel">
        <legend className="sr-only">Refine your search</legend>
        <div className="home-filter-heading"><strong>Refine your discovery</strong><button type="button" onClick={()=>setFilters(emptyFilters)}>Clear filters</button></div>
        {loading&&<p role="status"><LoaderCircle aria-hidden="true" size={14} className="spin"/>Loading available filters…</p>}
        {!!error&&<p role="alert">Some filters could not be loaded. Use “Try again” below to reload them.</p>}
        <div className="home-filter-fields">
          {([
            ['project_type','Project type',projectTypes,'All types'],
            ['domain','Mission domain',domains,'All mission domains'],
            ['organization','Organization',organizations,'All organizations'],
            ['status','Project status',projectStatuses,'All statuses'],
          ] as const).map(([key,label,values,placeholder])=><label key={key}>{label}<select value={filters[key]} onChange={e=>setFilters({...filters,[key]:e.target.value})}><option value="">{placeholder}</option>{values.map(value=><option key={value}>{value}</option>)}</select></label>)}
        </div>
        <p>Filters apply when you search. Leave the search field empty to browse matching projects.</p>
      </fieldset>}
    </form>
    <div className="home-suggestions"><span>Need a starting point?</span><div>{suggestions.map(suggestion=><button key={suggestion} type="button" onClick={()=>{setQuery(suggestion);search(suggestion)}}>{suggestion}</button>)}</div></div>
  </div>
}

function DiscoveryCard({count,label,description,to,loading}:{count?:number;label:string;description:string;to:string;loading:boolean}) {
  return <Link className="discovery-card" to={to}>
    <div className="discovery-value" aria-busy={loading}>{loading?<span className="stat-skeleton" aria-label="Loading count"/>:count===undefined?<span className="stat-unavailable">Unavailable</span>:count.toLocaleString()}</div>
    <h2>{label}</h2><p>{description}</p>
  </Link>
}

export function HomePage({user,renderProject}:{user:string;renderProject:(project:Project)=>ReactNode}) {
  const overview = useQuery({queryKey:[user,'/analytics/overview'],queryFn:()=>api<Overview>('/analytics/overview',user)})
  const organizations = useQuery({queryKey:[user,'/organizations'],queryFn:()=>api<string[]>('/organizations',user)})
  const {data} = overview
  const failed = overview.isError || organizations.isError

  return <div className="home-page">
    <div className="home-ambient" aria-hidden="true">
      <svg className="home-ship" viewBox="0 200 1920 720" aria-hidden="true">
        <defs>
          <clipPath id="home-uss-iowa-cutout">
            <path d="M170 756 174 739 190 739 195 720 203 686 218 657 228 643 239 653 246 703 257 714 286 716 306 721 332 728 361 731 371 708 379 697 389 704 399 729 434 732 447 724 459 729 465 735 495 738 511 711 523 700 536 705 551 737 575 739 588 726 596 697 606 675 618 679 626 732 649 738 668 724 681 682 692 663 704 668 712 723 738 726 754 708 768 678 780 672 791 684 799 721 834 718 849 679 861 656 876 643 887 626 901 612 916 605 933 581 950 565 963 538 976 523 993 517 1005 508 1027 506 1032 474 1045 462 1059 454 1073 407 1083 375 1090 331 1095 239 1107 239 1115 354 1128 377 1153 369 1168 383 1174 415 1191 432 1201 469 1214 461 1228 464 1241 482 1250 503 1284 507 1310 516 1334 538 1348 565 1370 569 1394 588 1423 594 1450 623 1486 635 1518 653 1552 658 1596 661 1640 666 1675 665 1711 659 1701 692 1664 713 1608 733 1544 753 1478 770 1404 790 1329 812 1240 833 1144 850 1042 869 928 884 801 893 655 903 520 909 396 909 303 897 245 878 220 846 200 805 185 780z"/>
          </clipPath>
        </defs>
        <image className="home-ship-image" href="/assets/uss-iowa.jpg" x="0" y="0" width="1920" height="1189" clipPath="url(#home-uss-iowa-cutout)"/>
      </svg>
      <span className="home-ambient-dots"/><span className="home-ambient-dots home-ambient-dots-secondary"/>
    </div>
    <section className="home-hero" aria-labelledby="home-title">
      <div className="home-introduction"><h1 id="home-title">Navy<span>LINK</span></h1>
      <h2>Find what the fleet is building.</h2>
      <p>Discover existing Navy capabilities, connect with organizations, and accelerate innovation across the fleet.</p></div>
      <HomeSearch domains={Object.keys(data?.domains||{}).sort()} organizations={organizations.data||[]} loading={overview.isPending||organizations.isPending} error={overview.error||organizations.error}/>
    </section>

    <div className="home-content">
      <div className="home-discovery-heading"><h2>Catalog</h2><span><ShieldCheck size={14} aria-hidden="true"/>Your authorized catalog view</span></div>
      {failed&&<div role="alert" className="home-data-error">Some catalog data could not be loaded.<button type="button" onClick={()=>{void overview.refetch();void organizations.refetch()}}>Try again</button></div>}
      <nav className="home-summary" aria-label="Catalog overview">
        <DiscoveryCard count={data?.total} label="Projects" description="Explore existing Navy initiatives and capabilities" to="/catalog" loading={overview.isPending}/>
        <DiscoveryCard count={data?Object.keys(data.domains).length:undefined} label="Mission Domains" description="Explore projects by mission area" to="/domains" loading={overview.isPending}/>
        <DiscoveryCard count={organizations.data?.length} label="Organizations" description="Connect with teams across the Navy" to="/organizations" loading={organizations.isPending}/>
      </nav>

      <section className="home-recent" aria-labelledby="home-recent-title">
        <div className="home-section-heading"><div><h2 id="home-recent-title">Recently updated on NavyLINK</h2><p>Explore the latest activity across the capability catalog.</p></div><Link to="/catalog">View All</Link></div>
        {overview.isPending?<div className="home-card-loading" role="status"><LoaderCircle aria-hidden="true" size={22} className="spin"/>Loading the latest projects…</div>:data?.recent.length?<div className="card-grid">{data.recent.slice(0,3).map(project=><div className="home-project" key={project.id}>{renderProject(project)}<span className="home-project-updated">Updated <time dateTime={project.last_updated}>{project.last_updated}</time></span></div>)}</div>:overview.isError?<div className="home-empty">Recent projects are unavailable. Use “Try again” above to reload the catalog.</div>:<div className="home-empty"><FolderOpen size={28} aria-hidden="true"/><h3>No projects to show yet</h3><p>Explore another demo identity or contribute a project to the catalog.</p><Link to="/projects/new">Register a project</Link></div>}
      </section>

      <section className="home-check" aria-labelledby="home-check-title">
        <span className="home-check-icon"><Workflow size={25} aria-hidden="true"/></span><div><h2 id="home-check-title">A new idea? Start with what exists.</h2><p>Find related tools, datasets, and collaborators before you build.</p></div><Button asChild variant="outline"><Link to="/check">Explore your idea</Link></Button>
      </section>
    </div>
  </div>
}
