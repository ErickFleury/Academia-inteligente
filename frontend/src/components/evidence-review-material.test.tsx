import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, expect, test } from 'vitest'

import type { EvidenceArtifact } from '../evidence-review'
import { EvidenceReviewMaterial } from './evidence-review-material'

afterEach(cleanup)
function material(kind: EvidenceArtifact['kind'], content: Record<string, unknown>): EvidenceArtifact {
  return { id: 'synthetic', kind, title: 'Material fictício', sha256: 'a'.repeat(64), content, sections: [], judgments: [], approval_ready: false, missing_items: [], independence_complete: false }
}
test('source reading exposes the original document, exact selected quotations and locators without JSON', () => {
  render(<EvidenceReviewMaterial artifact={material('source', { url: 'https://example.org/source', language: 'en', authors: ['Autoria fictícia'], chunks: [{ id: 'fixture:1', section: 'Trecho fictício', content: 'Original exposed fixture quotation.' }] })} />)
  expect(screen.getByRole('link', { name: 'Abrir fonte original em outra aba' })).toHaveAttribute('href', 'https://example.org/source')
  expect(screen.getByText('Original exposed fixture quotation.')).toHaveAttribute('lang', 'en')
  expect(screen.getByText(/Localização para citar no parecer: fixture:1/)).toBeInTheDocument()
  expect(screen.getByText(/não substituem o documento completo/)).toBeInTheDocument()
  expect(document.querySelector('pre')).toBeNull()
})
test('metadata-only sources explicitly disclose the missing passages and reject executable links', () => {
  render(<EvidenceReviewMaterial artifact={material('source', { url: 'javascript:alert(1)', chunks: [] })} />)
  expect(screen.getByText(/somente uma referência bibliográfica/)).toBeInTheDocument()
  expect(screen.queryByRole('link')).not.toBeInTheDocument()
})
test('a proposed rule shows parameters, decisions, applicable profiles and its actual references', () => {
  render(<EvidenceReviewMaterial artifact={material('rule_proposal', {
    proposal: { statement: 'Exposed synthetic proposal', parameters: [{ name: 'fixture_parameter', minimum: 2, maximum: 3, unit: 'rir' }], decision_needed: 'Synthetic decision needed' },
    sources: [{ id: 'REF1', url: 'https://example.org/study', locator: 'Table fixture' }],
    profiles: [{ goal_family: 'strength', population: 'Synthetic population', unresolved: ['Synthetic limitation'], runtime_eligible: false }],
  })} />)
  expect(screen.getByText('Exposed synthetic proposal')).toBeInTheDocument()
  expect(screen.getByText('Mínimo')).toBeInTheDocument()
  expect(screen.getByText('Repetições em reserva (RIR)')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Abrir referência REF1' })).toHaveAttribute('href', 'https://example.org/study')
  expect(screen.getByText(/Synthetic limitation/)).toBeInTheDocument()
  expect(screen.getByText('Força')).toBeInTheDocument()
  expect(screen.getByText('Não')).toBeInTheDocument()
})
test('public protocol reading exposes the actual criteria and budgets while explaining case custody', () => {
  render(<EvidenceReviewMaterial artifact={material('evaluation_protocol', { protocol: { title: 'Protocolo fictício', methods: 'Método fictício', decision_thresholds: 'Critério fictício', repeat_count: 2, maximum_writer_calls: 6, maximum_runtime_seconds: 90 }, case_count: 3 })} />)
  const section = within(screen.getByRole('region', { name: 'Material de leitura para avaliação' }))
  expect(section.getByText('Critério fictício')).toBeInTheDocument()
  expect(section.getByText('Limite total de chamadas ao modelo')).toBeInTheDocument()
  expect(section.getByText('6')).toBeInTheDocument()
  expect(section.getByText(/Somente o custodiante/)).toBeInTheDocument()
  expect(document.querySelector('pre')).toBeNull()
})
test('incomplete bundles show empty contracts and decisions as readable pending material', () => {
  render(<EvidenceReviewMaterial artifact={material('prescription_bundle', { policies: { policies: [{ status: 'pending', population: 'Synthetic population', decisions: [] }], dictionary: { exercises: [] } }, execution: { contracts: [] }, accounting: { mappings: [] } })} />)
  expect(screen.getByText('Synthetic population')).toBeInTheDocument()
  expect(screen.getByText('Pendente')).toBeInTheDocument()
  expect(screen.getByText('Contratos de execução')).toBeInTheDocument()
  expect(screen.getAllByText('Nenhum item documentado.')).toHaveLength(4)
})
