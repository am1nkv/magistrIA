import { useRef, useState } from 'react'
import { api } from '../api.js'

// Zone de dépôt : crée un nouveau dossier, ou ajoute des actes à un dossier existant (dossierId)
export default function Upload({ onDone, dossierId, compact }) {
  const [over, setOver] = useState(false)
  const [busy, setBusy] = useState(false)
  const [erreur, setErreur] = useState(null)
  const input = useRef()

  async function envoyer(fileList) {
    const files = [...fileList].filter((f) => f.name.toLowerCase().endsWith('.pdf'))
    if (!files.length) return setErreur('Seuls les fichiers PDF sont acceptés.')
    setBusy(true); setErreur(null)
    try {
      if (dossierId) await api.ajouterActes(dossierId, files)
      else await api.creer(files)
      onDone?.()
    } catch (e) {
      setErreur(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className={`dropzone ${over ? 'over' : ''} ${compact ? 'compact' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setOver(true) }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); envoyer(e.dataTransfer.files) }}
      onClick={() => input.current.click()}
    >
      <input ref={input} type="file" accept="application/pdf" multiple hidden onChange={(e) => envoyer(e.target.files)} />
      {busy ? <span><span className="spinner" /> Envoi…</span> : dossierId ? (
        <span><strong>+ Ajouter des actes</strong> (conclusions en réponse…) — la fiche sera régénérée sur l'ensemble du dossier</span>
      ) : (
        <>
          <strong>Déposer les actes d'un nouveau dossier</strong>
          <span className="muted">Assignation et conclusions d'un même dossier (PDF) — glisser-déposer ou cliquer</span>
        </>
      )}
      {erreur && <span className="error">{erreur}</span>}
    </div>
  )
}
