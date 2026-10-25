import type { PrescriptionOutcome, SavedPrescriptionDraft, ValidatedPrescription } from './training-prescription'

// Public synthetic development examples, never an independent evaluation set.
export const developmentPrescription: ValidatedPrescription = {
  prescription_eligibility: 'eligible', scope: 'session_sheet', policy_version: 'exemplo-1',
  projection: { name: 'Proposta fictícia', objective: 'Objetivo fictício para avaliação da interface', items: [{
    exercise_name: 'Agachamento (Dia A)', sets: 2, repetitions: '3–5', load_guidance: '2–3 RIR', rest_seconds: 30,
  }] },
  instructions: [{ session_id: 'sessao-a', item_id: 'item-1', progression: 'Progrida somente na condição revisada.', amount: '1', unit: 'repetitions', stop: 'Interrompa conforme a condição revisada.', regression: 'Retorne à etapa revisada pelo instrutor.', notes: [] }],
  knowledge_status: 'supported', knowledge_limitations: 'Exemplo fictício de desenvolvimento. Não representa recomendação de treino.',
  citations: [{ chunk_id: 'exemplo-1', source_id: 'exemplo', title: 'Fonte fictícia de desenvolvimento', url: 'https://example.test/evidence', authors: ['Autoria fictícia'], license: 'Exemplo', license_url: 'https://example.test/license', section: 'Trecho fictício' }],
  trace: [{ path: 'sessao-a/item-1/volume', label_pt_br: 'Agachamento — Séries e repetições', rule_id: 'regra-ficticia-volume', derivation: 'professionally_derived', evidence: [{ source_id: 'exemplo', passage_id: 'exemplo-1', locator: 'Trecho fictício', outcome: 'Desfecho fictício', certainty: 'low' }] }],
}
export const developmentAccepted: PrescriptionOutcome = { status: 'accepted', version_id: 'rascunho-ficticio', revision: 1, requires_instructor_review: true, prescription: developmentPrescription }
export const developmentSaved: SavedPrescriptionDraft = { id: 'rascunho-anterior-ficticio', revision: 2, qualification: 'legacy', projection: { ...developmentPrescription.projection, objective: 'Objetivo do rascunho anterior', items: [{ ...developmentPrescription.projection.items[0], exercise_name: 'Elevação de panturrilha (Dia A)' }] } }
