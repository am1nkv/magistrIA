import { fichierUrl } from '../api.js'

// Pastille « A · p. 4 · §12 » cliquable : ouvre le PDF de l'acte à la bonne page.
export function SourceLink({ source, docIds }) {
  const docId = docIds[source.doc]
  const label = `${source.doc} · p. ${source.page}${source.paragraphe ? ` · §${source.paragraphe}` : ''}`
  const verif = source.verifie === true ? '✓' : source.verifie === false ? '⚠' : ''
  const title = `${source.verifie === false ? 'Extrait non retrouvé mot pour mot — à contrôler.\n' : ''}« ${source.extrait} »`
  const cls = `source ${source.verifie === false ? 'unverified' : ''}`
  if (!docId) return <span className={cls} title={title}>{label} {verif}</span>
  return (
    <a className={cls} href={fichierUrl(docId, source.page)} target="_blank" rel="noreferrer" title={title}>
      {label} {verif}
    </a>
  )
}

export function Sources({ sources, docIds }) {
  if (!sources?.length) return null
  return (
    <span className="sources">
      {sources.map((s, i) => <SourceLink key={i} source={s} docIds={docIds} />)}
    </span>
  )
}
