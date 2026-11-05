import {useRef, useState} from 'react'
import {Link, NavLink, useLocation} from 'react-router-dom'
import {Menu, X} from 'lucide-react'

const logo = new URL('../assets/navylink-logo.png', import.meta.url).href

type Identity = {id:string; label:string; editor:boolean}

export function AppHeader({user, identities, onIdentityChange}:{
  user:string; identities?:Identity[]; onIdentityChange:(user:string)=>void
}) {
  const [open, setOpen] = useState(false)
  const menuToggle = useRef<HTMLButtonElement>(null)
  const location = useLocation()
  const registryActive = location.pathname==='/people'||location.pathname==='/datasources'
  const [menuLocation, setMenuLocation] = useState(location)
  if (menuLocation !== location) {
    setMenuLocation(location)
    setOpen(false)
  }

  return <header className="navy-header">
    <div className="navy-header-inner">
      <Link className="navy-brand" to="/" aria-label="NavyLINK home">
        <span className="navy-brand-mark"><img className="navy-brand-logo" src={logo} alt="NavyLINK" width={1055} height={931}/></span>
        <span className="navy-brand-copy">
          <span className="navy-brand-name">Navy<span className="brand-gold">LINK</span></span>
          <small>Discover. Connect. Innovate.</small>
        </span>
      </Link>
      <button ref={menuToggle} className="navy-menu-toggle" type="button" aria-label="Toggle navigation" aria-expanded={open} aria-controls="primary-navigation" onClick={()=>setOpen(!open)}>
        {open ? <X aria-hidden="true" size={24}/> : <Menu aria-hidden="true" size={24}/>}
      </button>
      <nav id="primary-navigation" className={'navy-navigation'+(open?' is-open':'')} aria-label="Main navigation" onKeyDown={e=>{if(e.key==='Escape'){setOpen(false);menuToggle.current?.focus()}}}>
        <NavLink to="/" end>Home</NavLink>
        <span className="navy-nav-divider" aria-hidden="true"/>
        <NavLink to="/catalog">Catalog</NavLink>
        <span className="navy-nav-divider" aria-hidden="true"/>
        <NavLink to="/librarian">Librarian</NavLink>
        <span className="navy-nav-divider" aria-hidden="true"/>
        <NavLink to="/check">Prebuild</NavLink>
        <span className="navy-nav-divider" aria-hidden="true"/>
        <Link to="/people" className={registryActive?'active':undefined} aria-current={registryActive?'page':undefined}>Registry</Link>
      </nav>
      <label className="navy-identity">Demo identity
        <select aria-label="Demo identity" value={user} onChange={e=>{onIdentityChange(e.target.value);setOpen(false)}}>
          {identities?.length ? identities.map(identity=><option key={identity.id} value={identity.id}>{identity.label}</option>) : <option value={user}>{user}</option>}
        </select>
      </label>
    </div>
  </header>
}
