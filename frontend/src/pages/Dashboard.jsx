import { useEffect, useMemo, useState } from 'react'
import { api, fmtDate } from '../api.js'
import Upload from '../components/Upload.jsx'

const TRIS = {
  priorite: { label: 'Priorité procédurale', fn: (a, b) => a.priorite_rang - b.priorite_rang },
  echeance: { label: 'Échéance la plus proche', fn: (a, b) => cmp(a.prochaine_echeance?.date, b.prochaine_echeance?.date) },
  recent: { label: 'Introduction (plus récent)', fn: (a, b) => cmp(b.date_introduction, a.date_introduction) },
  ancien: { label: 'Introduction (plus ancien)', fn: (a, b) => cmp(a.date_introduction, b.date_introduction) },
}

// Les valeurs manquantes vont toujours en bas
function cmp(x, y) {
  if (!x && !y) return 0
  if (!x) return 1
  if (!y) return -1
  return x < y ? -1 : x > y ? 1 : 0
}

export default function Dashboard() {
  const [dossiers, setDossiers] = useState([])
  const [erreur, setErreur] = useState(null)
  const [tri, setTri] = useState('priorite')
  const [matiere, setMatiere] = useState('')
  const [q, setQ] = useState('')

  const charger = () => api.dossiers().then(setDossiers).catch((e) => setErreur(e.message))
  useEffect(() => { charger() }, [])

  // Rafraîchit tant qu'une analyse est en cours : le dossier « arrive » tout seul dans le tableau
  const enCours = dossiers.some((d) => d.statut === 'analyse en cours')
  useEffect(() => {
    if (!enCours) return
    const t = setInterval(charger, 3000)
    return () => clearInterval(t)
  }, [enCours])

  const matieres = useMemo(() => [...new Set(dossiers.map((d) => d.matiere).filter(Boolean))].sort(), [dossiers])

  const visibles = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return dossiers
      .filter((d) => !matiere || d.matiere === matiere)
      .filter((d) => !needle || [
        d.rg, d.nature_affaire, d.juridiction, ...d.mots_cles, ...d.articles,
        ...d.parties.demandeur, ...d.parties.defendeur,
      ].some((v) => v?.toLowerCase().includes(needle)))
      .sort(TRIS[tri].fn)
  }, [dossiers, tri, matiere, q])

  return (
    <>
      <Upload onDone={charger} />

      <section className="card">
        <div className="toolbar">
          <h2>Dossiers <span className="muted">({visibles.length})</span></h2>
          <input className="search" placeholder="Rechercher : RG, partie, article, mot-clé…" value={q} onChange={(e) => setQ(e.target.value)} />
          <select value={matiere} onChange={(e) => setMatiere(e.target.value)}>
            <option value="">Toutes matières</option>
            {matieres.map((m) => <option key={m}>{m}</option>)}
          </select>
          <select value={tri} onChange={(e) => setTri(e.target.value)}>
            {Object.entries(TRIS).map(([k, v]) => <option key={k} value={k}>Trier : {v.label}</option>)}
          </select>
        </div>

        {tri === 'priorite' && (
          <p className="explain">
            Ordre de priorité <strong>procédural et explicable</strong> : 1) urgence invoquée par une partie,
            2) échéance la plus proche, 3) ancienneté du dossier. Aucun critère tiré du fond ni des chances de succès.
          </p>
        )}
        {erreur && <p className="error">{erreur}</p>}

        <table className="table">
          <thead>
            <tr>
              <th>#</th><th>N° RG</th><th>Parties</th><th>Matière</th><th>Introduit le</th>
              <th>Prochaine échéance</th><th>Textes cités</th><th>Statut</th>
            </tr>
          </thead>
          <tbody>
            {visibles.map((d) => (
              <tr key={d.id} onClick={() => { window.location.hash = `#/dossier/${d.id}` }}>
                <td>
                  <div className="rank">{d.priorite_rang}</div>
                </td>
                <td className="nowrap">
                  <strong>{d.rg || '—'}</strong>
                  {d.fictif && <div><span className="tag fictif">fictif</span></div>}
                </td>
                <td>
                  {d.statut === 'analyse en cours' ? <span className="muted">Analyse des actes…</span> : (
                    <>
                      <div>{d.parties.demandeur.join(', ') || '—'}</div>
                      <div className="muted">c/ {d.parties.defendeur.join(', ') || '—'}</div>
                      <div className="small">{d.nature_affaire}</div>
                    </>
                  )}
                </td>
                <td>{d.matiere && <span className="tag">{d.matiere}</span>}</td>
                <td className="nowrap">{fmtDate(d.date_introduction)}</td>
                <td>
                  {d.prochaine_echeance?.date ? (
                    <>
                      <strong className="nowrap">{fmtDate(d.prochaine_echeance.date)}</strong>
                      <div className="small">{d.prochaine_echeance.objet}</div>
                    </>
                  ) : '—'}
                  {d.priorite_motifs.length > 0 && (
                    <div className="why" title={d.priorite_motifs.join('\n')}>Pourquoi ce rang ? {d.priorite_motifs.join(' · ')}</div>
                  )}
                </td>
                <td className="small">{d.articles.slice(0, 3).join(' ; ') || '—'}</td>
                <td><Statut d={d} /></td>
              </tr>
            ))}
            {visibles.length === 0 && (
              <tr><td colSpan={8} className="muted center">Aucun dossier. Déposez une assignation ci-dessus.</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </>
  )
}

function Statut({ d }) {
  if (d.statut === 'analyse en cours') return <span className="status running"><span className="spinner" /> Analyse…</span>
  if (d.statut === 'erreur') return <span className="status err" title={d.erreur}>Erreur</span>
  return <span className="status draft">Brouillon IA<br /><span className="small">à valider</span></span>
}
