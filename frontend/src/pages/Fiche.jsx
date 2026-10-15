import { useEffect, useState } from 'react'
import { api, fichierUrl, fmtDate } from '../api.js'
import { Sources } from '../components/SourceLink.jsx'
import Upload from '../components/Upload.jsx'

const SECTIONS = [
  ['identification', '1. Identification'],
  ['mots-cles', '2. Mots-clés'],
  ['faits', '3. Faits'],
  ['contestes', '4. Faits contestés'],
  ['procedure', '5. Procédure'],
  ['moyens', '6. Moyens et prétentions'],
  ['textes', '7. Textes cités'],
  ['pieces', '8. Pièces'],
  ['vigilance', '9. Vigilance procédurale'],
]

export default function Fiche({ id }) {
  const [d, setD] = useState(null)
  const [erreur, setErreur] = useState(null)

  const charger = () => api.dossier(id).then(setD).catch((e) => setErreur(e.message))
  useEffect(() => { charger() }, [id])
  useEffect(() => {
    if (d?.statut !== 'analyse en cours') return
    const t = setInterval(charger, 3000)
    return () => clearInterval(t)
  }, [d?.statut])

  if (erreur) return <p className="error">{erreur}</p>
  if (!d) return <p className="muted">Chargement…</p>

  const f = d.fiche
  // Lettre d'acte -> id du fichier, pour les liens « p. N »
  const docIds = Object.fromEntries(d.documents.map((x) => [x.label, x.id]))

  return (
    <>
      <a href="#/" className="back">← Tous les dossiers</a>

      <div className="banner">
        Synthèse générée par IA — <strong>brouillon à valider</strong> — ne constitue pas une analyse du fond.
        Chaque élément renvoie à sa source : <span className="source">A · p. 4 ✓</span> = extrait retrouvé dans l'acte,
        <span className="source unverified">⚠</span> = à contrôler.
      </div>

      <section className="card head">
        <div>
          <h1>{f?.identification?.rg ? `RG ${f.identification.rg}` : `Dossier n° ${d.id}`}{d.fictif && <span className="tag fictif">fictif</span>}</h1>
          <div className="muted">
            {[f?.identification?.juridiction, f?.identification?.chambre].filter(Boolean).join(' — ')}
          </div>
          {f?.identification?.nature_affaire && <div className="nature">{f.identification.nature_affaire}</div>}
        </div>
        <div className="head-side">
          {f?.matiere && <span className="tag big">{f.matiere}</span>}
          {d.resume.priorite_motifs.length > 0 && (
            <div className="small">Priorité n° {d.resume.priorite_rang ?? '—'} : {d.resume.priorite_motifs.join(' · ')}</div>
          )}
          {!d.fictif && <button className="link danger" onClick={async () => { if (confirm('Supprimer ce dossier ?')) { await api.supprimer(d.id); window.location.hash = '#/' } }}>Supprimer</button>}
        </div>
      </section>

      <section className="card">
        <h3>Actes du dossier</h3>
        <ul className="actes">
          {(f?.actes?.length ? f.actes : d.documents.map((x) => ({ doc: x.label, intitule: x.filename, document_id: x.id }))).map((a) => (
            <li key={a.doc}>
              <span className="letter">{a.doc}</span>
              <span>
                <strong>{a.type_acte ? cap(a.type_acte) : 'Acte'}{a.numero ? ` n° ${a.numero}` : ''}{a.recapitulatives ? ' (récapitulatives)' : ''}</strong>
                {a.cote && <> — {a.cote === 'demandeur' ? 'Demandeur' : 'Défendeur'}{a.partie ? ` (${a.partie})` : ''}</>}
                {a.date && <span className="muted"> — {fmtDate(a.date)}</span>}
                <div className="small muted">{a.intitule}{a.nb_pages ? ` · ${a.nb_pages} p.` : ''}</div>
              </span>
              {(a.document_id || docIds[a.doc]) && (
                <a className="link" href={fichierUrl(a.document_id || docIds[a.doc])} target="_blank" rel="noreferrer">Ouvrir le PDF</a>
              )}
            </li>
          ))}
        </ul>
        {!d.fictif && <Upload dossierId={d.id} compact onDone={charger} />}
      </section>

      {d.statut === 'analyse en cours' && <section className="card center"><span className="spinner" /> Analyse des actes en cours…</section>}
      {d.statut === 'erreur' && (
        <section className="card">
          <p className="error">L'analyse a échoué : {d.erreur}</p>
          <button onClick={() => api.relancer(d.id).then(charger)}>Relancer l'analyse</button>
        </section>
      )}

      {f && d.statut !== 'analyse en cours' && (
        <>
          {f.alertes?.length > 0 && (
            <section className="card alertes">
              <h3>Contrôles automatiques</h3>
              <ul>{f.alertes.map((a, i) => <li key={i}>{a}</li>)}</ul>
            </section>
          )}

          <nav className="toc">
            {SECTIONS.map(([k, label]) => (
              <button key={k} onClick={() => document.getElementById(k)?.scrollIntoView({ behavior: 'smooth' })}>{label}</button>
            ))}
          </nav>

          <Section id="identification" title="1. Identification des parties">
            <VisAVis
              gauche={<Parties parties={f.identification.parties.filter((p) => p.cote === 'demandeur')} />}
              droite={<Parties parties={f.identification.parties.filter((p) => p.cote === 'defendeur')} />}
            />
            <dl className="meta">
              <dt>N° RG</dt><dd>{f.identification.rg || '—'}</dd>
              <dt>Juridiction</dt><dd>{f.identification.juridiction || '—'}</dd>
              <dt>Chambre</dt><dd>{f.identification.chambre || '—'}</dd>
              <dt>Date d'introduction</dt><dd>{fmtDate(f.identification.date_introduction)}</dd>
            </dl>
          </Section>

          <Section id="mots-cles" title="2. Mots-clés">
            <div className="tags">{f.mots_cles.map((m) => <span key={m} className="tag">{m}</span>)}</div>
          </Section>

          <Section id="faits" title={f.debat_contradictoire ? '3. Faits non contestés' : '3. Faits allégués par le demandeur — non encore débattus'}>
            {!f.debat_contradictoire && (
              <p className="explain">Un seul côté a produit des actes : aucun fait ne peut encore être qualifié de « non contesté ».</p>
            )}
            <Frise items={f.faits_non_contestes} docIds={docIds} />
          </Section>

          {f.debat_contradictoire && (
            <Section id="contestes" title="4. Faits contestés">
              {f.faits_contestes.length === 0 && <p className="muted">Aucun fait contesté relevé.</p>}
              {f.faits_contestes.map((fc, i) => (
                <div key={i} className="conteste">
                  <h4>{fc.objet}</h4>
                  <VisAVis
                    gauche={fc.demandeur ? <p>{fc.demandeur.texte} <Sources sources={fc.demandeur.sources} docIds={docIds} /></p> : <Vide />}
                    droite={fc.defendeur ? <p>{fc.defendeur.texte} <Sources sources={fc.defendeur.sources} docIds={docIds} /></p> : <Vide />}
                  />
                </div>
              ))}
            </Section>
          )}

          <Section id="procedure" title="5. Frise de la procédure">
            <Frise items={f.frise_procedure} docIds={docIds} />
            {f.prochaine_echeance && (
              <p className="echeance">
                Prochaine échéance : <strong>{fmtDate(f.prochaine_echeance.date)}</strong> — {f.prochaine_echeance.objet}
                <Sources sources={f.prochaine_echeance.sources} docIds={docIds} />
              </p>
            )}
            {f.urgence_declaree && (
              <p className="echeance">Urgence invoquée : {f.urgence_declaree.texte} <Sources sources={f.urgence_declaree.sources} docIds={docIds} /></p>
            )}
          </Section>

          <Section id="moyens" title="6. Moyens et prétentions">
            <h4 className="sub">Prétentions</h4>
            <VisAVis
              gauche={<Liste items={f.pretentions_demandeur} render={(p) => p.texte} docIds={docIds} />}
              droite={<Liste items={f.pretentions_defendeur} render={(p) => p.texte} docIds={docIds} />}
            />
            <h4 className="sub">Moyens</h4>
            <VisAVis
              gauche={<Moyens items={f.moyens_demandeur} docIds={docIds} />}
              droite={<Moyens items={f.moyens_defendeur} docIds={docIds} />}
            />
          </Section>

          <Section id="textes" title="7. Textes et jurisprudence cités par les parties">
            {f.textes_cites.length === 0 ? <Vide /> : (
              <table className="table compact">
                <thead><tr><th>Référence</th><th>Type</th><th>Cité par</th><th>Sources</th></tr></thead>
                <tbody>
                  {f.textes_cites.map((t, i) => (
                    <tr key={i}>
                      <td><a href={t.url} target="_blank" rel="noreferrer">{t.reference} ↗</a></td>
                      <td>{t.type === 'jurisprudence' ? 'Jurisprudence' : 'Texte'}</td>
                      <td>{t.cite_par.map((c) => (c === 'demandeur' ? 'Demandeur' : 'Défendeur')).join(', ') || '—'}</td>
                      <td><Sources sources={t.sources} docIds={docIds} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <p className="small muted">Seuls les textes et décisions expressément cités dans les actes sont repris ; les liens ouvrent une recherche Légifrance.</p>
          </Section>

          <Section id="pieces" title="8. Pièces communiquées">
            <VisAVis
              gauche={<Liste items={f.pieces.filter((p) => p.cote === 'demandeur')} render={(p) => `Pièce ${p.numero} — ${p.intitule}`} docIds={docIds} />}
              droite={<Liste items={f.pieces.filter((p) => p.cote === 'defendeur')} render={(p) => `Pièce ${p.numero} — ${p.intitule}`} docIds={docIds} />}
            />
          </Section>

          <Section id="vigilance" title="9. Points de vigilance procédurale">
            <p className="explain">Relevé des dates utiles et délais invoqués, <strong>à vérifier par le magistrat</strong>. L'outil ne se prononce ni sur la prescription ni sur la recevabilité.</p>
            {f.vigilance.length === 0 ? <Vide /> : f.vigilance.map((v, i) => (
              <div key={i} className="vigil">
                <strong>{v.objet}</strong> <Sources sources={v.sources} docIds={docIds} />
                <ul>
                  {v.texte_invoque && <li>Texte invoqué : {v.texte_invoque}</li>}
                  {v.delai && <li>Délai : {v.delai}</li>}
                  {v.dates_utiles.map((x, j) => <li key={j}>{x}</li>)}
                </ul>
              </div>
            ))}
          </Section>

          {d.similaires.length > 0 && (
            <section className="card">
              <h3>Dossiers de même matière / mots-clés communs</h3>
              <ul className="similaires">
                {d.similaires.map((s) => (
                  <li key={s.id}><a href={`#/dossier/${s.id}`}>{s.rg ? `RG ${s.rg}` : `Dossier ${s.id}`}</a> — {s.nature_affaire} <span className="muted">({s.raisons.join(' ; ')})</span></li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </>
  )
}

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1)

function Section({ id, title, children }) {
  return <section id={id} className="card"><h3>{title}</h3>{children}</section>
}

// Contradictoire : deux colonnes strictement symétriques, ordre fixe, même style
function VisAVis({ gauche, droite }) {
  return (
    <div className="visavis">
      <div><div className="side-label">Demandeur</div>{gauche}</div>
      <div><div className="side-label">Défendeur</div>{droite}</div>
    </div>
  )
}

const Vide = () => <p className="muted">Rien de relevé dans les actes.</p>

function Parties({ parties }) {
  if (!parties.length) return <Vide />
  return parties.map((p, i) => (
    <div key={i} className="partie">
      <strong>{p.nom}</strong>{p.qualite && <span className="muted"> — {p.qualite}</span>}
      <div className="small">{p.avocat ? `Avocat : ${p.avocat}${p.barreau ? ` (barreau de ${p.barreau})` : ''}` : 'Avocat : —'}</div>
    </div>
  ))
}

function Frise({ items, docIds }) {
  if (!items?.length) return <Vide />
  return (
    <ol className="frise">
      {items.map((e, i) => (
        <li key={i}>
          <span className="date">{fmtDate(e.date)}</span>
          <span>{e.description} <Sources sources={e.sources} docIds={docIds} /></span>
        </li>
      ))}
    </ol>
  )
}

function Liste({ items, render, docIds }) {
  if (!items?.length) return <Vide />
  return <ul className="liste">{items.map((x, i) => <li key={i}>{render(x)} <Sources sources={x.sources} docIds={docIds} /></li>)}</ul>
}

function Moyens({ items, docIds }) {
  if (!items?.length) return <Vide />
  return items.map((m, i) => (
    <div key={i} className="moyen">
      <strong>{m.intitule}</strong>
      <p>{m.expose} <Sources sources={m.sources} docIds={docIds} /></p>
    </div>
  ))
}
