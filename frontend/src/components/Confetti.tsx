import type { CSSProperties } from 'react'

const COLORS = ['#6c4cf1', '#ff6b8b', '#ffc93c', '#22c28a', '#3aa0ff']

// Fixed pseudo-random pieces, so renders (and tests) are deterministic.
const PIECES = Array.from({ length: 28 }, (_, index) => ({
  left: `${(index * 37) % 100}%`,
  background: COLORS[index % COLORS.length],
  '--delay': `${(index % 7) * 70}ms`,
  '--drift': `${((index * 53) % 120) - 60}px`,
  '--spin': `${((index * 97) % 720) - 360}deg`,
}))

/** A short, decorative confetti burst (hidden with reduced motion). */
export function Confetti() {
  return (
    <div className="confetti" aria-hidden>
      {PIECES.map((style, index) => (
        <span key={index} style={style as CSSProperties} />
      ))}
    </div>
  )
}
