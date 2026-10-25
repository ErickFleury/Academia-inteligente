export type DoseDetails = {
  mode: 'resistance' | 'aerobic' | 'flexibility' | 'balance' | 'functional'
  dose: Record<string, unknown>
  rest?: { kind: string; seconds: number | null } | null
  group?: { group_id: string; kind: 'pair' | 'circuit'; rounds: number; order: number; rest: { kind: string; seconds: number | null } } | null
}

export function trainingRest(seconds: number | null, details?: DoseDetails | null) {
  const rest = details?.group?.rest ?? details?.rest
  if (rest?.kind === 'not_applicable' || seconds === null && !rest) return 'Não se aplica'
  const relations: Record<string, string> = { after_pair: 'após o par', after_round: 'após a volta', after_exercise: 'após o exercício', between_attempts: 'entre tentativas', between_holds: 'entre sustentações', between_tasks: 'entre tarefas' }
  return `${rest?.seconds ?? seconds} s${rest && relations[rest.kind] ? ` ${relations[rest.kind]}` : ''}`
}

export function trainingCount(sets: number | null) { return sets === null ? '—' : String(sets) }
