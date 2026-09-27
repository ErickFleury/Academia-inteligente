import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'
import { EquipmentManagementPage } from './equipment-management-page'

const model = { id: 'm1', name: 'Leg press', description: 'Plataforma inclinada', image_url: null, image_link: null, image_source: 'none', active_quantity: 2, active: true, brand: 'Marca interna', category: 'Pernas', manufacturer_model: 'LP-45', created_at: '', updated_at: '' }
const unit = { id: 'u1', equipment_model_id: 'm1', label: 'LP-01', active: true, operational_state: 'out_of_order', location: 'Sala 1', serial_number: '123', created_at: '', updated_at: '' }
const ok = (body: unknown) => ({ ok: true, json: async () => body })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
function setup(override?: (url: string, init?: RequestInit) => unknown) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => override?.(url, init) ?? (url.endsWith('/units') ? ok([unit]) : ok([model, { ...model, id: 'm2', name: 'Esteira', category: 'Cardio', active: false }])))
  vi.stubGlobal('fetch', fetchMock)
  render(<MemoryRouter><EquipmentManagementPage accessToken="token" onSignOut={vi.fn()} /></MemoryRouter>)
  return fetchMock
}
async function details() { fireEvent.click(await screen.findByRole('button', { name: 'Ver detalhes de Leg press' })); return screen.findByRole('dialog', { name: 'Leg press' }) }

test('searches internal fields and keeps editing inside equipment details', async () => {
  setup()
  await screen.findByRole('heading', { name: 'Esteira' })
  fireEvent.change(screen.getByRole('textbox', { name: 'Buscar equipamento' }), { target: { value: 'pernas' } })
  expect(screen.queryByRole('heading', { name: 'Esteira' })).not.toBeInTheDocument()
  const panel = await details()
  expect(within(panel).getByText('LP-45')).toBeInTheDocument()
  fireEvent.click(within(panel).getByRole('button', { name: 'Editar equipamento' }))
  expect(await screen.findByRole('dialog', { name: 'Editar equipamento' })).toBeInTheDocument()
  expect(screen.getByRole('textbox', { name: 'Nome do equipamento' })).toHaveValue('Leg press')
})

test('creates model and initial units in one submission and opens its details', async () => {
  let release!: () => void
  const fetchMock = setup((url, init) => init?.method === 'POST' ? new Promise((resolve) => { release = () => resolve(ok({ ...model, name: 'Nova máquina', active_quantity: 3 })) }) : undefined)
  await screen.findByRole('heading', { name: 'Leg press' })
  fireEvent.click(screen.getByRole('button', { name: 'Novo equipamento' }))
  fireEvent.change(screen.getByRole('textbox', { name: 'Nome do equipamento' }), { target: { value: 'Nova máquina' } })
  fireEvent.change(screen.getByRole('textbox', { name: 'Marca' }), { target: { value: 'Marca privada' } })
  fireEvent.click(screen.getByRole('button', { name: 'Continuar' }))
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Quantidade inicial' }), { target: { value: '3' } })
  fireEvent.change(screen.getByRole('textbox', { name: 'Prefixo dos identificadores' }), { target: { value: 'MAQ' } })
  fireEvent.click(screen.getByRole('button', { name: 'Cadastrar equipamento' }))
  expect(screen.getByRole('button', { name: 'Salvando...' })).toBeDisabled()
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1)
  const body = JSON.parse(fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')![1]!.body as string)
  expect(body).toMatchObject({ name: 'Nova máquina', initial_quantity: 3, unit_prefix: 'MAQ', brand: 'Marca privada' })
  release()
  expect(await screen.findByRole('dialog', { name: 'Nova máquina' })).toBeInTheDocument()
})

test('preserves entered registration fields after server validation fails', async () => {
  setup((_, init) => init?.method === 'POST' ? { ok: false, status: 422, json: async () => ({ detail: [{ loc: ['body', 'name'], msg: 'English provider detail' }] }) } : undefined)
  await screen.findByRole('heading', { name: 'Leg press' })
  fireEvent.click(screen.getByRole('button', { name: 'Novo equipamento' }))
  fireEvent.change(screen.getByRole('textbox', { name: 'Nome do equipamento' }), { target: { value: 'Meu equipamento' } })
  fireEvent.click(screen.getByRole('button', { name: 'Continuar' }))
  fireEvent.click(screen.getByRole('button', { name: 'Cadastrar equipamento' }))
  await screen.findByText('Verifique os campos informados.')
  fireEvent.click(screen.getByRole('button', { name: 'Voltar' }))
  expect(screen.getByRole('textbox', { name: 'Nome do equipamento' })).toHaveValue('Meu equipamento')
  expect(screen.getByText('Verifique o campo nome.')).toBeInTheDocument()
  expect(screen.queryByText('English provider detail')).not.toBeInTheDocument()
})

test('edits unit metadata while preserving its separate operational state', async () => {
  const fetchMock = setup((_, init) => init?.method === 'PATCH' ? ok({ ...unit, label: 'LP-99', location: 'Sala 2' }) : undefined)
  const panel = await details()
  fireEvent.click(within(panel).getByRole('tab', { name: /Unidades físicas/ }))
  expect(await within(panel).findByText('Fora de serviço')).toBeInTheDocument()
  fireEvent.click(within(panel).getByRole('button', { name: 'Editar LP-01' }))
  fireEvent.change(screen.getByRole('textbox', { name: 'Identificador interno' }), { target: { value: 'LP-99' } })
  fireEvent.change(screen.getByRole('textbox', { name: 'Localização na academia' }), { target: { value: 'Sala 2' } })
  fireEvent.click(screen.getByRole('button', { name: 'Salvar unidade' }))
  expect(await within(panel).findByRole('heading', { name: 'LP-99' })).toBeInTheDocument()
  expect(within(panel).getByText('Fora de serviço')).toBeInTheDocument()
  const body = JSON.parse(fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')![1]!.body as string)
  expect(body).toEqual({ label: 'LP-99', location: 'Sala 2', serial_number: '123' })
})

test('deactivation requires confirmation and cancellation makes no request', async () => {
  const fetchMock = setup((_, init) => init?.method === 'PATCH' ? ok({ ...model, active: false }) : undefined)
  const panel = await details()
  fireEvent.click(within(panel).getByRole('button', { name: 'Desativar modelo' }))
  fireEvent.click(within(await screen.findByRole('dialog', { name: 'Confirmar alteração no inventário' })).getByRole('button', { name: 'Cancelar' }))
  await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Confirmar alteração no inventário' })).not.toBeInTheDocument())
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(false)
  fireEvent.click(within(panel).getByRole('button', { name: 'Desativar modelo' }))
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar alteração' }))
  expect(await within(panel).findByText('Oculto do catálogo')).toBeInTheDocument()
})

test('adds a unit batch through the single batch endpoint', async () => {
  const fetchMock = setup((_, init) => init?.method === 'POST' ? ok([unit, { ...unit, id: 'u2' }]) : undefined)
  const panel = await details()
  fireEvent.click(within(panel).getByRole('tab', { name: /Unidades físicas/ }))
  fireEvent.click(within(panel).getByRole('button', { name: 'Adicionar unidades' }))
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Quantidade' }), { target: { value: '2' } })
  fireEvent.click(screen.getByRole('button', { name: 'Adicionar' }))
  await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Adicionar unidades' })).not.toBeInTheDocument())
  const write = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')!
  expect(write[0]).toMatch(/\/units\/batch$/)
  expect(JSON.parse(write[1]!.body as string)).toEqual({ quantity: 2, prefix: 'UN' })
})
