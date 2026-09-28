import type { SessionItem } from '../api/learning'
import { articleOf } from '../lib/fun'
import { ITEM_TYPE_LABELS, STATUS_LABELS } from '../lib/labels'

export function WordCard({ item }: { item: SessionItem }) {
  const word = item.vocabulary_item
  const article = articleOf(word)
  const grammar = [
    word.prateritum && ['Präteritum', word.prateritum],
    word.perfekt && ['Perfekt', word.perfekt],
    word.preposition && [
      'Edat',
      word.grammatical_case ? `${word.preposition} + ${word.grammatical_case}` : word.preposition,
    ],
    !word.preposition && word.grammatical_case && ['Hal', word.grammatical_case],
  ].filter((entry): entry is [string, string] => Array.isArray(entry))

  return (
    <li className={`card word${article ? ` word--${article}` : ''}`}>
      <div className="word__head">
        <span className="word__number">{item.position}</span>
        <span className={`badge badge--status-${item.status}`}>{STATUS_LABELS[item.status]}</span>
      </div>
      <h3 className="word__german" lang="de">
        {word.german}
      </h3>
      <p className="word__turkish">
        {word.turkish} <span className="muted">({ITEM_TYPE_LABELS[word.item_type]})</span>
      </p>
      {grammar.length > 0 && (
        <dl className="word__grammar">
          {grammar.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd lang="de">{value}</dd>
            </div>
          ))}
        </dl>
      )}
      {word.example_german && (
        <blockquote className="word__example">
          <p lang="de">{word.example_german}</p>
          {word.example_turkish && <p className="muted">{word.example_turkish}</p>}
        </blockquote>
      )}
      {word.source_page && <p className="word__source muted">PDF sayfa {word.source_page}</p>}
    </li>
  )
}
