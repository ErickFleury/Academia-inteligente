import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useLayoutEffect } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'

import type { EvidenceArtifact, EvidenceSeal } from './evidence-review'
import { InstructorEvidenceReviewPage } from './instructor-evidence-review-page'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })
const artifact: EvidenceArtifact = {
  id: 'source:fixture', kind: 'source', title: 'Fonte fictícia para revisão', sha256: 'a'.repeat(64),
  approval_ready: true, missing_items: [], independence_complete: false,
  sections: [{ label: 'Trecho fictício', text: 'Evidência sintética de teste.' }],
  content: { synthetic: true }, judgments: [],
}
const protocol = { title: 'Avaliação fictícia protegida', scope: 'Teste', methods: 'Método fictício', decision_thresholds: 'Critério somente de teste.', repeat_count: 1, maximum_writer_calls: 1, maximum_runtime_seconds: 10 }
const seal: EvidenceSeal = { id: 'seal-1', custodian_name: 'Outro instrutor', protocol, artifact_hashes: { [artifact.id]: artifact.sha256 }, case_count: 1, payload_sha256: 'b'.repeat(64), created_at: '2026-10-24T10:00:00Z', can_read_cases: false, status: 'custody_registered_evaluation_and_release_pending' }
const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body })
function defaultResponse(url: string) {
  return ok(url.endsWith('/artifacts') ? [artifact] : url.endsWith('/seals') ? [] : artifact)
}
function page(onSignOut = vi.fn()) {
  return render(<MemoryRouter><InstructorEvidenceReviewPage accessToken="instructor-session" onSignOut={onSignOut} /></MemoryRouter>)
}
async function choose(label: string, option: string) {
  fireEvent.mouseDown(await screen.findByLabelText(new RegExp('^' + label + '[\\s*]*$')))
  fireEvent.click(within(await screen.findByRole('listbox')).getByRole('option', { name: option }))
}

test('registers an attributable version-bound judgment without selecting a certainty or approval automatically', async () => {
  const fetchMock = vi.fn().mockImplementation(async (url: string, init: RequestInit) => init.method === 'POST' ? ok({ id: 'review-1' }) : defaultResponse(url))
  vi.stubGlobal('fetch', fetchMock)
  page()
  await choose('Artefato para revisão', artifact.title)
  const formElement = await screen.findByLabelText('Registrar parecer', { selector: 'form' })
  const form = within(formElement)
  const inputs = Array.from(formElement.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>('input,textarea'))
  act(() => { for (const [label, value] of [
    ['Escopo e população avaliados', 'Escopo exclusivamente sintético'], ['Método de avaliação e versão', 'Instrumento fictício v1'],
    ['Fundamentação do parecer', 'Parecer de teste sobre conteúdo fictício, sem aprovação real.'],
    ['Qualificação e experiência para esta revisão', 'Declaração fictícia de teste'], ['Declaração de conflitos de interesse', 'Declaração fictícia, sem conflito neste teste'],
    ['Domínio avaliado 1', 'Domínio fictício'], ['Julgamento do domínio 1', 'Necessita de alterações no exemplo'],
    ['Localização da evidência 1', 'fixture:1'], ['Desfecho avaliado 1', 'Desfecho fictício'], ['Justificativa da certeza 1', 'Não foi realizada avaliação científica neste teste'],
  ]) {
    const input = inputs.find((element) => Array.from(element.labels ?? []).some((associatedLabel) => associatedLabel.textContent?.replace(/\s*\*\s*$/, '').trim() === label))
    expect(input, `Associated input for ${label}`).toBeDefined()
    fireEvent.change(input!, { target: { value } })
  } })
  expect(form.getByLabelText('Certeza do desfecho 1')).toHaveTextContent('Não avaliada')
  expect(form.getByLabelText('Decisão do parecer')).toHaveTextContent('Solicitar alterações')
  expect(form.getByLabelText('Função da revisão')).toHaveTextContent('Revisão metodológica')
  const submit = form.getByText('Registrar parecer desta versão', { selector: 'button' })
  expect(submit).toBeDisabled()
  fireEvent.click(form.getByLabelText(/Declaro que realizei pessoalmente/))
  fireEvent.click(submit)
  expect(await screen.findByText(/Parecer registrado nesta versão/)).toBeInTheDocument()
  const posts = fetchMock.mock.calls.filter(([, init]) => init.method === 'POST')
  expect(posts).toHaveLength(1)
  expect(posts[0][1].headers.Authorization).toBe('Bearer instructor-session')
  expect(JSON.parse(posts[0][1].body)).toMatchObject({ expected_artifact_sha256: artifact.sha256, decision: 'changes_requested', personally_performed: true })
  expect(JSON.parse(posts[0][1].body)).toMatchObject({
    scope: 'Escopo exclusivamente sintético', method_and_version: 'Instrumento fictício v1',
    competence: 'Declaração fictícia de teste',
    judgments: [{ domain: 'Domínio fictício', judgment: 'Necessita de alterações no exemplo', source_locator: 'fixture:1' }],
    outcomes: [{ outcome: 'Desfecho fictício', certainty: 'not_assessed', rationale: 'Não foi realizada avaliação científica neste teste' }],
  })
  expect(JSON.parse(posts[0][1].body)).not.toHaveProperty('reviewer_subject')
})

test('incomplete contracts never expose an enabled approval action', async () => {
  const incomplete = { ...artifact, approval_ready: false, missing_items: ['Faltam decisões de prescrição.'] }
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => ok(url.endsWith('/artifacts') ? [incomplete] : url.endsWith('/seals') ? [] : incomplete)))
  page()
  await choose('Artefato para revisão', artifact.title)
  expect(await screen.findByText('Faltam decisões de prescrição.')).toBeInTheDocument()
  await choose('Decisão do parecer', 'Aprovar o conteúdo revisado')
  fireEvent.click(screen.getByRole('checkbox', { name: /Declaro que realizei pessoalmente/ }))
  expect(screen.getByRole('button', { name: 'Registrar parecer desta versão' })).toBeDisabled()
})

test('owner acceptance is visible without claiming a professional or independent review', async () => {
  const accepted = { ...artifact, owner_approval: { decision_id: 'owner-fixture', authority: 'project_owner', decided_on: '2026-10-24', professional_review_performed: false, independent_evaluation_performed: false } }
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => ok(url.endsWith('/artifacts') ? [accepted] : url.endsWith('/seals') ? [] : accepted)))
  page()
  await choose('Artefato para revisão', artifact.title)
  expect(await screen.findByText(/Aprovado por decisão do proprietário/)).toHaveTextContent('Sem parecer profissional')
  expect(screen.getByText('A revisão independente desta versão ainda não está concluída.')).toBeInTheDocument()
  expect(screen.getByText('Nenhum parecer registrado para este artefato.')).toBeInTheDocument()
})

test('readiness is fetched intentionally and separates accepted rules from enabled profiles', async () => {
  const fetchMock = vi.fn().mockImplementation(async (url: string) => url.endsWith('/readiness') ? ok({ rules: [{ owner_accepted: true }], profiles: [{ compiled_policy_ids: [] }], enabled_cohorts: [], missing_items: ['Faltam escolhas de protocolo.'] }) : defaultResponse(url))
  vi.stubGlobal('fetch', fetchMock)
  page()
  const button = await screen.findByRole('button', { name: 'Consultar prontidão dos contratos' })
  await waitFor(() => expect(button).toBeEnabled())
  expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/readiness'))).toBe(false)
  fireEvent.click(button)
  expect(await screen.findByRole('region', { name: 'Prontidão dos contratos' })).toHaveTextContent('1 regras com aprovação do proprietário')
  expect(screen.getByText('Faltam escolhas de protocolo.')).toBeInTheDocument()
  expect(screen.getByText(/0 famílias com políticas compiladas; 0 perfis liberados/)).toBeInTheDocument()
})

test('approval requires an assessed outcome, explicit independence and a review deadline', async () => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => defaultResponse(url)))
  page()
  await choose('Artefato para revisão', artifact.title)
  await choose('Decisão do parecer', 'Aprovar o conteúdo revisado')
  const form = within(screen.getByRole('form', { name: 'Registrar parecer' }))
  const submit = form.getByRole('button', { name: 'Registrar parecer desta versão' })
  fireEvent.click(form.getByLabelText(/Declaro que realizei pessoalmente/))
  expect(submit).toBeDisabled()
  await choose('Certeza do desfecho 1', 'Moderada')
  expect(submit).toBeDisabled()
  fireEvent.change(form.getByLabelText(/Prazo para nova revisão/), { target: { value: '2099-01-01' } })
  expect(submit).toBeDisabled()
  fireEvent.click(form.getByLabelText(/Declaro a independência/))
  expect(submit).toBeEnabled()
  fireEvent.change(form.getByLabelText(/Prazo para nova revisão/), { target: { value: '' } })
  expect(submit).toBeDisabled()
})

test('other instructors see seal metadata without a case-reading action or answer content', async () => {
  const fetchMock = vi.fn().mockImplementation(async (url: string) => ok(url.endsWith('/artifacts') ? [artifact] : [seal]))
  vi.stubGlobal('fetch', fetchMock)
  page()
  await screen.findByRole('combobox', { name: 'Artefato para revisão' })
  fireEvent.click(screen.getByRole('tab', { name: 'Custódia da avaliação' }))
  expect(screen.getByText('Casos e respostas restritos à conta do responsável.')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Abrir casos sob minha custódia/ })).not.toBeInTheDocument()
  expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/cases'))).toBe(false)
})

test('changing sessions removes custodian-only case content before paint', async () => {
  const own = { ...seal, can_read_cases: true }
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => ok(
    url.endsWith('/artifacts') ? [artifact] : url.endsWith('/seals') ? [own]
      : { id: own.id, payload_sha256: own.payload_sha256, cases: [{ case_id: 'private-fixture', cohort: 'synthetic', scenario: 'Exposed fixture scenario', reference_judgment: 'PRIVATE-FIXTURE-ANSWER', critical: true }] },
  )))
  const snapshots: string[] = []
  function SessionPage({ token }: { token: string }) {
    useLayoutEffect(() => { snapshots.push(document.body.textContent ?? '') }, [token])
    return <InstructorEvidenceReviewPage accessToken={token} onSignOut={vi.fn()} />
  }
  const view = render(<MemoryRouter><SessionPage token="first" /></MemoryRouter>)
  await screen.findByRole('combobox', { name: 'Artefato para revisão' })
  fireEvent.click(screen.getByRole('tab', { name: 'Custódia da avaliação' }))
  fireEvent.click(screen.getByRole('button', { name: /Abrir casos sob minha custódia/ }))
  expect(await screen.findByText(/PRIVATE-FIXTURE-ANSWER/)).toBeInTheDocument()
  view.rerender(<MemoryRouter><SessionPage token="second" /></MemoryRouter>)
  expect(snapshots.at(-1)).not.toContain('PRIVATE-FIXTURE-ANSWER')
  expect(screen.queryByText(/PRIVATE-FIXTURE-ANSWER/)).not.toBeInTheDocument()
})

test('a custodian intentionally registers synthetic cases with prespecified budgets and a frozen artifact hash', async () => {
  let registered = false
  const fetchMock = vi.fn().mockImplementation(async (url: string, init: RequestInit) => {
    if (init.method === 'POST') { registered = true; return ok({ ...seal, can_read_cases: true }) }
    return ok(url.endsWith('/artifacts') ? [artifact] : registered ? [{ ...seal, can_read_cases: true }] : [])
  })
  vi.stubGlobal('fetch', fetchMock)
  page()
  await screen.findByRole('combobox', { name: 'Artefato para revisão' })
  fireEvent.click(screen.getByRole('tab', { name: 'Custódia da avaliação' }))
  await choose('Artefato de referência', artifact.title)
  const form = within(screen.getByRole('form', { name: 'Registrar custódia da avaliação' }))
  act(() => { for (const [label, value] of [
    ['Título da avaliação', 'Avaliação exclusivamente fictícia'], ['Perfis e objetivos da avaliação', 'Perfil sintético de teste'], ['Métodos e partições da avaliação', 'Método fictício de teste'],
    ['Critérios e limites de aprovação definidos antes da execução', 'Critérios fictícios para verificar o formulário, sem aprovação real.'],
    ['Repetições por caso', '1'], ['Limite total de chamadas ao modelo', '1'], ['Limite total de execução em segundos', '10'],
    ['Identificador do caso 1', 'fixture-1'], ['Perfil sintético 1', 'synthetic'], ['Descrição do caso sintético 1', 'Caso fictício e exposto de teste'], ['Julgamento de referência privado 1', 'PRIVATE-REFERENCE-FIXTURE'],
  ]) fireEvent.change(form.getByLabelText(new RegExp('^' + label + '[\\s*]*$')), { target: { value } }) })
  for (const name of [/Confirmo que todos os casos/, /Confirmo a independência/, /Entendo que registrar a custódia/]) fireEvent.click(form.getByLabelText(name))
  fireEvent.click(form.getByRole('button', { name: 'Registrar custódia e proteger casos' }))
  expect(await screen.findByText(/Custódia registrada\. Os casos/)).toBeInTheDocument()
  expect(screen.queryByDisplayValue('PRIVATE-REFERENCE-FIXTURE')).not.toBeInTheDocument()
  const post = fetchMock.mock.calls.find(([, init]) => init.method === 'POST')
  expect(JSON.parse(post?.[1].body)).toMatchObject({ artifact_hashes: { [artifact.id]: artifact.sha256 }, protocol: { repeat_count: 1, maximum_writer_calls: 1 }, synthetic_only: true, independent_and_unexposed: true })
  expect(fetchMock.mock.calls.every(([url]) => !url.includes('/api/chat'))).toBe(true)
})

test('expired authorization signs out without exposing raw provider errors', async () => {
  const onSignOut = vi.fn()
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({ detail: 'PRIVATE-DIAGNOSTICS' }) }))
  page(onSignOut)
  await waitFor(() => expect(onSignOut).toHaveBeenCalledOnce())
  expect(await screen.findByText('Sua sessão expirou. Entre novamente.')).toBeInTheDocument()
  expect(screen.queryByText('PRIVATE-DIAGNOSTICS')).not.toBeInTheDocument()
})

test('material kinds separate proposed rules from sources and explain absent evaluation protocols', async () => {
  const rule = { ...artifact, id: 'rule:fixture', kind: 'rule_proposal', title: 'Regra fictícia', content: { proposal: { statement: 'Exposed synthetic statement' }, sources: [], profiles: [] } }
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => ok(url.endsWith('/artifacts') ? [artifact, rule] : url.endsWith('/seals') ? [] : rule)))
  page()
  await choose('Tipo de material', 'Regra proposta (1)')
  await choose('Artefato para revisão', rule.title)
  expect(await screen.findByText('Exposed synthetic statement')).toBeInTheDocument()
  expect(screen.getByText('Dados técnicos da versão (opcional)').closest('details')).not.toHaveAttribute('open')
  await choose('Tipo de material', 'Protocolo de avaliação (0)')
  expect(screen.getByText(/Nenhum protocolo de avaliação foi cadastrado/)).toBeInTheDocument()
  expect(screen.queryByText('Exposed synthetic statement')).not.toBeInTheDocument()
})
