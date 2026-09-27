import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'
import { InstructorEquipmentPage } from './instructor-equipment-page'
const model = { id:'model',name:'Leg Press',active_quantity:2 }
const unit = { id:'unit',label:'Unidade A',active:true,operational_state:'operational',revision:1 }
const ok = (body: unknown) => ({ ok:true,json:async()=>body })
afterEach(()=>{cleanup();vi.unstubAllGlobals()})
function setup(override?: (url:string,init?:RequestInit)=>unknown) {
  const mock=vi.fn(async(url:string,init?:RequestInit)=>override?.(url,init) ?? (url.includes('/units?')?ok({items:[unit,{...unit,id:'inactive',label:'Unidade inativa',active:false}],next_cursor:null}):ok({items:[model],next_cursor:null})))
  vi.stubGlobal('fetch',mock);render(<MemoryRouter><InstructorEquipmentPage accessToken="token" onSignOut={vi.fn()}/></MemoryRouter>);return mock
}
test('shows exact states and confirms only the operational change, preserving quantity',async()=>{
  const fetchMock=setup((_,init)=>init?.method==='PATCH'?ok({...unit,operational_state:'out_of_order',revision:2}):undefined)
  fireEvent.click(await screen.findByRole('button',{name:'Ver unidades'}))
  fireEvent.click(await screen.findByRole('button',{name:'Marcar fora de serviço: Unidade A'}))
  await screen.findByRole('dialog',{name:'Marcar fora de serviço'})
  fireEvent.click(screen.getByRole('button',{name:'Cancelar'}))
  await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  expect(fetchMock.mock.calls.some(([,init])=>init?.method==='PATCH')).toBe(false)
  fireEvent.click(screen.getByRole('button',{name:'Marcar fora de serviço: Unidade A'}))
  fireEvent.click(await screen.findByRole('button',{name:'Confirmar alteração'}))
  await screen.findByText('Estado operacional atualizado. A quantidade de inventário não foi alterada.')
  expect(screen.getByText('2 unidades ativas no inventário')).toBeInTheDocument()
  expect(screen.getByText('Fora de serviço')).toBeInTheDocument()
  expect(await screen.findByRole('button',{name:'Voltar a operacional: Unidade A'})).toBeEnabled()
  const write=fetchMock.mock.calls.find(([,init])=>init?.method==='PATCH')!
  expect(JSON.parse(write[1]!.body as string)).toEqual({operational_state:'out_of_order',expected_revision:1})
  expect(screen.queryByRole('button',{name:/Marcar fora de serviço: Unidade inativa/})).not.toBeInTheDocument()
})
test('stale toggle requires reloading units',async()=>{
  setup((_,init)=>init?.method==='PATCH'?{ok:false,status:409}:undefined)
  fireEvent.click(await screen.findByRole('button',{name:'Ver unidades'}))
  fireEvent.click(await screen.findByRole('button',{name:'Marcar fora de serviço: Unidade A'}))
  fireEvent.click(await screen.findByRole('button',{name:'Confirmar alteração'}))
  await screen.findByText('A unidade mudou ou foi desativada. Recarregue antes de continuar.')
  expect(await screen.findByRole('button',{name:'Marcar fora de serviço: Unidade A'})).toBeDisabled()
  fireEvent.click(screen.getByRole('button',{name:'Recarregar unidades'}))
  await waitFor(()=>expect(screen.getByRole('button',{name:'Marcar fora de serviço: Unidade A'})).toBeEnabled())
})
test('empty and failed lists offer clear feedback',async()=>{
  let fail=true
  setup(()=>fail?{ok:false,status:503}:ok({items:[],next_cursor:null}))
  await screen.findByText('Não foi possível carregar ou atualizar os equipamentos. Tente novamente.')
  fail=false;fireEvent.click(screen.getByRole('button',{name:'Recarregar equipamentos'}))
  await screen.findByText('Nenhum equipamento ativo')
})
