import {useRef, useState} from 'react'
import {Link, NavLink, useLocation} from 'react-router-dom'
import {Compass, GitCompareArrows, Menu, Plus, X} from 'lucide-react'

type Identity = {id:string; label:string; editor:boolean}

export function AppHeader({user, identities, selectedCount, onIdentityChange}:{
  user:string; identities?:Identity[]; selectedCount:number; onIdentityChange:(user:string)=>void
}) {
  const [open, setOpen] = useState(false)
  const menuToggle = useRef<HTMLButtonElement>(null)
  const location = useLocation()
  const [menuLocation, setMenuLocation] = useState(location)
  if (menuLocation !== location) {
    setMenuLocation(location)
    setOpen(false)
  }

  return <header className="navy-header">
    <div className="navy-header-inner">
      <Link className="navy-brand" to="/" aria-label="NavyLINK home">
        <span className="navy-brand-mark"><Compass size={29} strokeWidth={1.5} aria-hidden="true"/></span>
        <span>Navy<span className="brand-gold">LINK</span><small>Connecting Navy innovation</small></span>
      </Link>
      <button ref={menuToggle} className="navy-menu-toggle" type="button" aria-label="Toggle navigation" aria-expanded={open} aria-controls="primary-navigation" onClick={()=>setOpen(!open)}>
        {open ? <X aria-hidden="true" size={24}/> : <Menu aria-hidden="true" size={24}/>}
      </button>
      <nav id="primary-navigation" className={'navy-navigation'+(open?' is-open':'')} aria-label="Main navigation" onKeyDown={e=>{if(e.key==='Escape'){setOpen(false);menuToggle.current?.focus()}}}>
        <NavLink to="/" end>Home</NavLink>
        <NavLink to="/catalog">Catalog</NavLink>
        <NavLink to="/check">Check before you build</NavLink>
        <NavLink to="/assistant">Discovery assistant</NavLink>
        <NavLink to="/people">People & data</NavLink>
        <NavLink to="/compare" className="nav-compare"><GitCompareArrows size={16} aria-hidden="true"/>Compare{selectedCount>0&&<span>{selectedCount}</span>}</NavLink>
        <NavLink to="/projects/new" className="nav-register"><Plus size={15} aria-hidden="true"/>Register project</NavLink>
      </nav>
      <label className="navy-identity">Demo identity
        <select aria-label="Demo identity" value={user} onChange={e=>{onIdentityChange(e.target.value);setOpen(false)}}>
          {identities?.length ? identities.map(identity=><option key={identity.id} value={identity.id}>{identity.label}</option>) : <option value={user}>{user}</option>}
        </select>
      </label>
    </div>
  </header>
}
