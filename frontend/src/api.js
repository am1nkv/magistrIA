async function req(path, options) {
  const res = await fetch(`/api${path}`, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Erreur ${res.status}`)
  }
  return res.json()
}

function formData(files) {
  const fd = new FormData()
  for (const f of files) fd.append('files', f)
  return fd
}

export const api = {
  status: () => req('/status'),
  dossiers: () => req('/dossiers'),
  dossier: (id) => req(`/dossiers/${id}`),
  creer: (files) => req('/dossiers', { method: 'POST', body: formData(files) }),
  ajouterActes: (id, files) => req(`/dossiers/${id}/actes`, { method: 'POST', body: formData(files) }),
  relancer: (id) => req(`/dossiers/${id}/relancer`, { method: 'POST' }),
  supprimer: (id) => req(`/dossiers/${id}`, { method: 'DELETE' }),
}

export const fichierUrl = (docId, page) => `/api/files/${docId}${page ? `#page=${page}` : ''}`

export function fmtDate(d) {
  if (!d) return '—'
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(d)
  return m ? `${m[3]}/${m[2]}/${m[1]}` : d
}
