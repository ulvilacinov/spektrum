import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { json, mockApi, renderRoute } from '../test/utils'

function openGrammar() {
  mockApi({ 'GET /api/documents': () => json([]) })
  renderRoute('/')
  return userEvent.click(screen.getByRole('button', { name: /Dilbilgisi/ }))
}

describe('GrammarHelp', () => {
  it('opens the rules from the header on every page', async () => {
    await openGrammar()

    const dialog = screen.getByRole('dialog', { name: /Dilbilgisi kuralları/ })
    expect(within(dialog).getByRole('table', { name: 'Dört hal' })).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: /Haller/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('shows how der / die / das and ein change by case', async () => {
    await openGrammar()

    await userEvent.click(screen.getByRole('button', { name: /Artikeller/ }))

    const table = screen.getByRole('table', { name: 'Belirli artikel: der, die, das' })
    const dative = within(table).getByRole('row', { name: /^Dativ/ })
    expect(dative).toHaveTextContent('dem')
    expect(within(dative).getAllByRole('cell')[1]).toHaveTextContent('der')
    const indefinite = screen.getByRole('table', { name: 'Belirsiz artikel: ein, eine' })
    expect(within(indefinite).getByRole('row', { name: /^Akkusativ/ })).toHaveTextContent('einen')
  })

  it('answers "eine neues Haus?" in the adjective rules', async () => {
    await openGrammar()

    await userEvent.click(screen.getByRole('button', { name: /Sıfatlar/ }))

    expect(screen.getByText('„eine neues Haus“ mu?', { exact: false })).toBeInTheDocument()
    expect(screen.getAllByText(/ein neu/)[0]).toBeInTheDocument()
    expect(screen.getByRole('table', { name: '2) ein, kein, mein … sonrası' })).toBeInTheDocument()
  })

  it('highlights the endings', async () => {
    await openGrammar()
    await userEvent.click(screen.getByRole('button', { name: /Artikeller/ }))

    const table = screen.getByRole('table', { name: 'Belirli artikel: der, die, das' })
    const cell = within(within(table).getByRole('row', { name: /^Dativ/ })).getAllByRole('cell')[0]
    expect(cell.querySelector('mark')).toHaveTextContent('em')
  })

  it('closes and reopens on the last topic', async () => {
    await openGrammar()
    await userEvent.click(screen.getByRole('button', { name: /Edatlar/ }))

    await userEvent.click(screen.getByRole('button', { name: 'Kapat' }))
    expect(screen.queryByRole('table')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Dilbilgisi/ }))
    expect(screen.getByRole('table', { name: 'Edatlar ve halleri' })).toBeInTheDocument()
  })
})
