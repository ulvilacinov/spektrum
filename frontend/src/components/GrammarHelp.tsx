import { Fragment, useEffect, useRef, useState } from 'react'

import { GRAMMAR, type GrammarBlock, type GrammarTable } from '../lib/grammar'

const GENDER_CLASSES = ['g-der', 'g-die', 'g-das', 'g-pl']

/** Renders the grammar markup: parts in [brackets] are highlighted. */
function Marked({ text }: { text: string }) {
  return text
    .split(/\[([^\]]+)\]/)
    .map((part, index) =>
      index % 2 === 1 ? <mark key={index}>{part}</mark> : <Fragment key={index}>{part}</Fragment>,
    )
}

function Table({ table }: { table: GrammarTable }) {
  const genderClass = (index: number) => (table.genders ? GENDER_CLASSES[index] : undefined)
  return (
    <figure className="grammar__table-wrap">
      <table className="grammar__table">
        <caption>{table.caption}</caption>
        <thead>
          <tr>
            <td />
            {table.columns.map((column, index) => (
              <th key={column} scope="col" className={genderClass(index)}>
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row) => (
            <tr key={row.label}>
              <th scope="row">{row.label}</th>
              {row.cells.map((cell, index) => (
                <td key={index} className={genderClass(index)} lang="de">
                  <Marked text={cell} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {table.note && (
        <figcaption className="muted">
          <Marked text={table.note} />
        </figcaption>
      )}
    </figure>
  )
}

function Block({ block }: { block: GrammarBlock }) {
  if (block.kind === 'table') return <Table table={block} />
  if (block.kind === 'tip') {
    return (
      <aside className="grammar__tip">
        <h4>💡 {block.title}</h4>
        {block.text.map((line) => (
          <p key={line}>
            <Marked text={line} />
          </p>
        ))}
      </aside>
    )
  }
  return (
    <section>
      <h4>{block.title}</h4>
      <ul className="grammar__list">
        {block.items.map((item) => (
          <li key={item}>
            <Marked text={item} />
          </li>
        ))}
      </ul>
    </section>
  )
}

/** A header button that opens the static grammar reference in a modal. */
export function GrammarHelp() {
  const dialog = useRef<HTMLDialogElement>(null)
  const [open, setOpen] = useState(false)
  // Kept while the app is open, so the modal reopens where the learner left it.
  const [sectionId, setSectionId] = useState(GRAMMAR[0].id)
  const section = GRAMMAR.find((item) => item.id === sectionId) ?? GRAMMAR[0]

  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal()
  }, [open])

  return (
    <>
      <button type="button" className="header__help" onClick={() => setOpen(true)}>
        📖 Dilbilgisi
      </button>
      <dialog
        ref={dialog}
        className="grammar"
        aria-labelledby="grammar-title"
        onClose={() => setOpen(false)}
        // A click on the backdrop (outside the content box) closes the modal.
        onClick={(event) => event.target === dialog.current && dialog.current?.close()}
      >
        {open && (
          <div className="grammar__box">
            <div className="grammar__head">
              <h2 id="grammar-title">📖 Dilbilgisi kuralları</h2>
              <button
                type="button"
                className="secondary grammar__close"
                aria-label="Kapat"
                onClick={() => dialog.current?.close()}
              >
                ✕
              </button>
            </div>
            <nav className="grammar__tabs" aria-label="Konular">
              {GRAMMAR.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={item.id === section.id ? undefined : 'secondary'}
                  aria-pressed={item.id === section.id}
                  onClick={() => setSectionId(item.id)}
                >
                  {item.emoji} {item.title}
                </button>
              ))}
            </nav>
            <div className="grammar__body">
              <p className="muted">{section.intro}</p>
              {section.blocks.map((block, index) => (
                <Block key={`${section.id}-${index}`} block={block} />
              ))}
            </div>
          </div>
        )}
      </dialog>
    </>
  )
}
