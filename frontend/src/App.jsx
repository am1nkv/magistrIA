import { useEffect, useState } from 'react'
import Dashboard from './pages/Dashboard.jsx'
import Fiche from './pages/Fiche.jsx'
import { api } from './api.js'

// Navigation minimale par hash : #/ (tableau de bord) ou #/dossier/12
function useRoute() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onChange = () => { setHash(window.location.hash); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  const m = /^#\/dossier\/(\d+)/.exec(hash)
  return m ? { page: 'fiche', id: Number(m[1]) } : { page: 'dashboard' }
}

export default function App() {
  const route = useRoute()
  const [status, setStatus] = useState(null)
  useEffect(() => { api.status().then(setStatus).catch(() => setStatus({ llm: false, hors_ligne: true })) }, [])

  return (
    <>
      <header className="topbar">
        <a href="#/" className="brand">Magistr<span>IA</span></a>
        <span className="tagline">Prise en main des dossiers — sans juger à la place du juge</span>
        {status && (
          <span className={`pill ${status.llm ? 'ok' : 'warn'}`}>
            {status.hors_ligne ? 'API hors ligne' : status.llm ? `Modèle : ${status.modele}` : 'Mode démo (cache)'}
          </span>
        )}
      </header>
      <main className="container">
        {route.page === 'fiche' ? <Fiche id={route.id} /> : <Dashboard />}
      </main>
      <footer className="footer">
        Outil d'aide à la lecture. Les synthèses sont des brouillons générés par IA, à valider par le magistrat ;
        elles ne constituent ni une analyse du fond ni une aide à la décision.
      </footer>
    </>
  )
}
