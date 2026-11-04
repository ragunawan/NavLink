import {Link} from 'react-router-dom'
import {ArrowUpRight} from 'lucide-react'
import type {Comparison} from '../api'

export function ProjectComparison({comparison}:{comparison:Comparison}) {
  const rows = [
    ['mission_problem','Mission problem'],['description','Description'],['intended_users','Intended users'],['domain','Mission domain'],['datasets','Associated datasets'],
    ['technical_summary','Technical approach'],['technologies','Technology stack'],['status','Status'],
    ['organization','Owning organization'],['access_instructions','Access instructions'],
    ['license','License / reuse terms'],['deployment','Deployment'],['integration','Integration'],
  ] as const
  return <>
    <div className="comparison-table"><table aria-label="Side-by-side project comparison">
      <thead><tr><th scope="col">Catalog evidence</th>{comparison.projects.map(p=><th scope="col" key={p.id}><Link to={'/projects/'+p.id}>{p.name}<ArrowUpRight size={15}/></Link></th>)}</tr></thead>
      <tbody>{rows.map(([field,label])=><tr key={field}><th scope="row">{label}</th>{comparison.projects.map(p=><td key={p.id} className={p[field]!=null&&p[field]!==''&&(!Array.isArray(p[field])||p[field].length>0)&&comparison.projects.every(other=>JSON.stringify(other[field])===JSON.stringify(p[field]))?'shared-attribute':'different-attribute'}>{field==='datasets'?p.datasets.map(d=>d.name).join(', ')||'No datasets stated':Array.isArray(p[field])?(p[field] as string[]).join(', ')||'Not stated':p[field]||'Unknown — confirm with owner'}</td>)}</tr>)}</tbody>
    </table></div>
    <p className="fine-print">Shaded cells have identical stated attributes. Unknown metadata remains unverified.</p><div className="comparison-findings"><h3>Similarities</h3><ul>{comparison.similarities.map(s=><li key={s}>{s}</li>)}</ul><h3>Potential collaboration</h3><ul>{comparison.collaboration_opportunities.length?comparison.collaboration_opportunities.map(s=><li key={s}>{s}</li>):<li>No explicit collaborator-seeking status stated; discuss fit with the owners.</li>}</ul><h3>Potential overlap</h3><p>{comparison.potential_overlap}</p><p>Shared datasets: {comparison.shared_datasets.join(', ')||'None stated'}</p><p>Shared tags: {comparison.shared_tags.join(', ')||'None stated'}</p><h3>Key differences</h3><ul>{comparison.differences.map(d=><li key={d}>{d}</li>)}</ul><h3>Reuse considerations</h3><ul>{comparison.open_questions.map(q=><li key={q}>{q}</li>)}</ul></div>
  </>
}
