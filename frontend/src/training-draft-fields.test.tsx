import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, expect, test, vi } from 'vitest'
import { TrainingDraftFields } from './training-draft-fields'
import type { ReviewContent } from './training-review'
const content: ReviewContent = { name: 'Força', objective: 'Treinar', items: [{ exercise_name: 'Leg Press', sets: 3, repetitions: '8', rest_seconds: 60, load_guidance: 'Leve', equipment_model_id: 'old', equipment_requirement: 'Modelo histórico' }] }
function Form() { const [draft, setDraft] = useState(content); return <><TrainingDraftFields accessToken="token" draft={draft} onChange={setDraft}/><output data-testid="draft">{JSON.stringify(draft)}</output></> }
afterEach(()=>{cleanup();vi.unstubAllGlobals()})
const ok=(body:unknown)=>({ok:true,json:async()=>body})

test('preserves historical snapshot without silently replacing it; new options use authenticated usable endpoint',async()=>{
  const fetchMock=vi.fn(async()=>ok({items:[{id:'usable',name:'Modelo operacional'}],next_cursor:null}))
  vi.stubGlobal('fetch',fetchMock);render(<Form/>);
  await waitFor(()=>expect(screen.getByRole('combobox')).not.toHaveAttribute('aria-disabled','true'))
  expect(screen.getByText('Referência preservada: Modelo histórico')).toBeInTheDocument()
  expect(JSON.parse(screen.getByTestId('draft').textContent!).items[0].equipment_model_id).toBe('old')
  fireEvent.mouseDown(screen.getByRole('combobox'))
  expect(screen.getByRole('option',{name:'Modelo histórico'})).toHaveAttribute('aria-disabled','true')
  fireEvent.click(screen.getByRole('option',{name:'Modelo operacional'}))
  expect(JSON.parse(screen.getByTestId('draft').textContent!).items[0]).toMatchObject({equipment_model_id:'usable',equipment_requirement:'Modelo operacional'})
  expect(fetchMock.mock.calls).toHaveLength(1)
  expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/instructor/equipment/usable-models?limit=20')
  expect(vi.mocked(fetch).mock.calls[0][1]?.headers).toMatchObject({Authorization:'Bearer token'})
})

test('loads bounded options and recovers from catalog failure without clearing retained content',async()=>{
  let failed=true
  vi.stubGlobal('fetch',vi.fn(async(url:string)=>failed?{ok:false,status:503}:ok({items:[{id:url.includes('cursor=')?'second':'first',name:url.includes('cursor=')?'Segundo':'Primeiro'}],next_cursor:url.includes('cursor=')?null:'next'})))
  render(<Form/>);await screen.findByText(/Não foi possível consultar/)
  expect(screen.getByRole('combobox')).toHaveAttribute('aria-disabled','true')
  failed=false;fireEvent.click(screen.getByRole('button',{name:'Recarregar equipamentos para prescrição'}))
  fireEvent.click(await screen.findByRole('button',{name:'Carregar mais opções de equipamento'}))
  await waitFor(()=>expect(screen.queryByRole('button',{name:'Carregar mais opções de equipamento'})).not.toBeInTheDocument())
  fireEvent.mouseDown(screen.getByRole('combobox'))
  expect(screen.getByRole('option',{name:'Primeiro'})).toBeInTheDocument()
  expect(screen.getByRole('option',{name:'Segundo'})).toBeInTheDocument()
  fireEvent.click(screen.getByRole('option',{name:'Sem equipamento do catálogo'}))
  expect(JSON.parse(screen.getByTestId('draft').textContent!).items[0]).toMatchObject({equipment_model_id:null,equipment_requirement:null})
})
