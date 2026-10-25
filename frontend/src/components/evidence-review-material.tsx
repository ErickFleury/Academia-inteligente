import { Alert, Box, Button, Divider, Stack, Typography } from '@mui/material'

import type { EvidenceArtifact } from '../evidence-review'

export const materialKindLabels: Record<EvidenceArtifact['kind'], string> = {
  source: 'Fonte de consulta', rule_proposal: 'Regra proposta',
  prescription_bundle: 'Políticas de treino', evaluation_protocol: 'Protocolo de avaliação',
}
const ruleNames: Record<string, string> = {
  RESISTANCE_EFFORT: 'Esforço no treino resistido', SOURCE_PAIRED_RESISTANCE: 'Programa de exercícios resistidos da fonte',
  SOURCE_MEDICINE_BALL_POWER: 'Programa de potência com medicine ball', SOURCE_ENDURANCE_CIRCUIT: 'Circuito de resistência muscular da fonte',
  SELECT_RESISTANCE: 'Seleção de exercícios resistidos', STRENGTH_DOSE: 'Dose de treino para força',
  NOVICE_LOADING: 'Cargas para iniciantes', HYPERTROPHY_VOLUME: 'Volume para hipertrofia', HYPERTROPHY_LOADING: 'Cargas para hipertrofia',
  STRENGTH_REST: 'Descanso no treino de força', HYPERTROPHY_REST: 'Descanso no treino de hipertrofia', LOAD_PROGRESSION: 'Progressão de carga',
  ENDURANCE_DOSE: 'Dose para resistência muscular', ENDURANCE_SETS: 'Séries para resistência muscular', POWER_DOSE: 'Dose para potência',
  POWER_STRUCTURE: 'Organização do treino de potência', POWER_REPETITIONS: 'Repetições para potência', AEROBIC_DOSE: 'Dose de exercício aeróbico',
  AEROBIC_INTENSITY: 'Intensidade do exercício aeróbico', AEROBIC_START_PROGRESS: 'Início e progressão do exercício aeróbico',
  AEROBIC_RECOVERY: 'Recuperação no exercício aeróbico', FLEXIBILITY_DOSE: 'Dose de exercícios de flexibilidade',
  FLEXIBILITY_STRUCTURE: 'Organização dos exercícios de flexibilidade', FLEXIBILITY_NEWER_EVIDENCE: 'Evidências recentes sobre flexibilidade',
  BALANCE_DOSE: 'Dose de exercícios de equilíbrio', FALL_PREVENTION: 'Prevenção de quedas', BALANCE_RECOVERY: 'Recuperação nos exercícios de equilíbrio',
  FUNCTION_DOSE: 'Dose do treino de capacidade funcional', FUNCTION_STRUCTURE: 'Organização do treino de capacidade funcional',
  WEIGHT_DIRECTION: 'Direcionamento para controle do peso', SPORT_SPECIFICITY: 'Especificidade para o esporte', RESTRICTIONS: 'Restrições e aplicabilidade',
  RESISTANCE_ACCOUNTING: 'Contabilização do treino resistido', AEROBIC_ACCOUNTING: 'Contabilização do exercício aeróbico',
  FLEXIBILITY_ACCOUNTING: 'Contabilização dos exercícios de flexibilidade', BALANCE_FUNCTION_ACCOUNTING: 'Contabilização do equilíbrio e da capacidade funcional',
  COMBINED_GOALS: 'Combinação de objetivos',
}
export function reviewMaterialTitle(artifact: EvidenceArtifact) {
  const rule = artifact.id.startsWith('rule:') ? ruleNames[artifact.id.slice(5)] : undefined
  return rule ? `Regra proposta: ${rule}` : artifact.id === 'source:nhs-flexibility' ? 'Exercícios de flexibilidade — NHS' : artifact.title
}
const guidance: Record<EvidenceArtifact['kind'], string> = {
  source: 'Leia a fonte original e confira se os trechos selecionados mantêm seu sentido, a quem se aplicam e quais são as limitações. Os trechos usados pelo sistema não substituem o documento completo.',
  rule_proposal: 'Confira a recomendação proposta, seus parâmetros, as fontes e a população atendida. Avalie se a tradução da evidência em uma regra de treino é justificada e quais decisões ainda faltam.',
  prescription_bundle: 'Confira a aplicação conjunta das políticas, os exercícios, os limites e as decisões pendentes. Uma regra isolada não representa uma política de treino completa.',
  evaluation_protocol: 'Confira os objetivos, os métodos, os critérios de aprovação e o orçamento definidos antes da execução. Os casos e as respostas de referência continuam restritos ao custodiante.',
}
const labels: Record<string, string> = {
  id: 'Identificador para referência', version: 'Versão', status: 'Situação',
  statement: 'Recomendação proposta — texto original', parameters: 'Parâmetros propostos',
  name: 'Parâmetro', unit: 'Unidade', minimum: 'Mínimo', maximum: 'Máximo',
  inputs: 'Informações necessárias', decision_needed: 'Decisão profissional pendente — texto original',
  kind: 'Natureza da recomendação', goal_family: 'Objetivo', population: 'População — texto original',
  dimensions: 'Regras por dimensão', selection: 'Seleção de exercícios', volume: 'Volume',
  intensity: 'Intensidade', frequency: 'Frequência', rest: 'Descanso', progression: 'Progressão',
  restrictions: 'Restrições', accounting: 'Contabilização do treino',
  unresolved: 'Lacunas — texto original', unresolved_decisions: 'Decisões pendentes — texto original',
  branch_resolution: 'Combinação das recomendações — texto original',
  coverage_status: 'Cobertura', runtime_eligible: 'Liberada para uso automático',
  protocol_alternatives: 'Alternativas de programa', experience_levels: 'Níveis de experiência',
  exclusions: 'Exclusões — texto original', restriction_interactions: 'Interações com restrições — texto original',
  exact_goal_mappings: 'Objetivos reconhecidos', decisions: 'Decisões de prescrição',
  dictionary: 'Dicionário de exercícios', exercises: 'Exercícios', mappings: 'Regras de contabilização',
  contracts: 'Contratos de execução', dictionary_version: 'Versão do dicionário',
  review_due_at: 'Prazo de revisão', review_records: 'Referências dos pareceres',
  schema_version: 'Versão do formato', doi: 'DOI', locator: 'Onde conferir na fonte',
  policies: 'Políticas documentadas', title: 'Título', scope: 'Perfis e objetivos',
  methods: 'Métodos e partições', decision_thresholds: 'Critérios e limites de aprovação',
  repeat_count: 'Repetições por caso', maximum_writer_calls: 'Limite total de chamadas ao modelo',
  maximum_runtime_seconds: 'Limite total em segundos',
  access: 'Disponibilidade — texto original', rights: 'Limites de reutilização — texto original',
}
const values: Record<string, string> = {
  pending: 'Pendente', partial_awaiting_review: 'Cobertura parcial, aguardando revisão',
  pending_professional_review_and_operational_evaluation: 'Aguardando revisão profissional e avaliação operacional',
  strength: 'Força', hypertrophy: 'Hipertrofia', none: 'Sem experiência', beginner: 'Iniciante',
  intermediate: 'Intermediário', advanced: 'Avançado', direct_recommendation: 'Recomendação da fonte',
  conservative_translation: 'Tradução conservadora proposta', rir: 'Repetições em reserva (RIR)',
}
function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}
function rows(value: unknown): Record<string, unknown>[] { return Array.isArray(value) ? value.map(object) : [] }
function text(value: unknown) { return typeof value === 'string' ? values[value] ?? (ruleNames[value] ? `${ruleNames[value]} (${value})` : value) : typeof value === 'boolean' ? value ? 'Sim' : 'Não' : value == null ? 'Não informado' : String(value) }
function ExternalLink({ url, children }: { url: unknown; children: string }) {
  if (typeof url !== 'string' || !/^https?:\/\//i.test(url)) return null
  return <Button component="a" href={url} target="_blank" rel="noopener noreferrer" variant="outlined" sx={{ alignSelf: 'flex-start', whiteSpace: 'normal' }}>{children}</Button>
}
function ReadableFields({ data }: { data: Record<string, unknown> }) {
  return <Stack spacing={1.5}>{Object.entries(data).map(([key, value]) => <Box key={key}>
    <Typography variant="subtitle2">{labels[key] ?? 'Informação complementar'}</Typography>
    {Array.isArray(value) ? value.length ? <Stack spacing={1} sx={{ pl: 2 }}>{value.map((item, index) => typeof item === 'object' && item !== null
      ? <Box key={index} sx={{ borderLeft: '2px solid', borderColor: 'divider', pl: 2 }}><ReadableFields data={object(item)} /></Box>
      : <Typography key={index} variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>• {text(item)}</Typography>)}</Stack> : <Typography variant="body2">Nenhum item documentado.</Typography>
      : value !== null && typeof value === 'object' ? <Box sx={{ pl: 2 }}><ReadableFields data={object(value)} /></Box>
        : <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{text(value)}</Typography>}
  </Box>)}</Stack>
}
export function EvidenceReviewMaterial({ artifact }: { artifact: EvidenceArtifact }) {
  const data = artifact.content ?? {}
  return <Stack spacing={2} component="section" aria-label="Material de leitura para avaliação">
    <Typography component="h3" variant="h4">O que avaliar neste material</Typography>
    <Typography>{guidance[artifact.kind]}</Typography>
    {artifact.kind === 'source' ? <>
      <Typography variant="body2">Título na fonte original: {artifact.title}</Typography>
      <ExternalLink url={data.url}>Abrir fonte original em outra aba</ExternalLink>
      <Typography variant="body2">Autoria: {Array.isArray(data.authors) ? data.authors.join('; ') : 'Não informada'}</Typography>
      <Typography variant="body2">Idioma da fonte: {data.language === 'en' ? 'Inglês. Os trechos abaixo preservam o texto original.' : data.language === 'pt' || data.language === 'pt-BR' ? 'Português' : text(data.language)}</Typography>
      <Typography component="h3" variant="h4">Trechos selecionados para o sistema</Typography>
      {!rows(data.chunks).length && <Alert severity="info">Há somente uma referência bibliográfica cadastrada. Consulte o documento original; não há trechos disponíveis aqui.</Alert>}
      {rows(data.chunks).map((chunk, index) => <Box key={index} component="article" sx={{ borderLeft: '3px solid', borderColor: 'divider', pl: 2 }}>
        <Typography component="h4" variant="subtitle1">{text(chunk.section)}</Typography>
        <Typography component="blockquote" lang={data.language === 'en' ? 'en' : undefined} sx={{ m: 0, mt: 1, whiteSpace: 'pre-wrap' }}>{text(chunk.content)}</Typography>
        <Typography variant="caption">Localização para citar no parecer: {text(chunk.id)}</Typography>
      </Box>)}
      {Array.isArray(data.limitations) && <ReadableFields data={{ restrictions: data.limitations }} />}
      <Typography variant="body2">A licença permite verificar as condições de reutilização; ela não comprova qualidade científica ou aprovação profissional.</Typography>
      <ExternalLink url={data.license_url}>Consultar condições da licença</ExternalLink>
    </> : artifact.kind === 'rule_proposal' ? <>
      <Alert severity="info">Esta é uma proposta para revisão, ainda sem liberação automática. Os textos de pesquisa abaixo estão no idioma original; não são uma aprovação.</Alert>
      <ReadableFields data={object(data.proposal)} />
      <Typography component="h3" variant="h4">Fontes que sustentam a proposta</Typography>
      {rows(data.sources).map((source, index) => <Stack key={index} spacing={1}>
        <Typography variant="subtitle2">Referência {text(source.id)}</Typography>
        <ExternalLink url={source.url}>{`Abrir referência ${text(source.id)}`}</ExternalLink>
        <ReadableFields data={Object.fromEntries(Object.entries(source).filter(([key]) => key !== 'url' && key !== 'id'))} />
      </Stack>)}
      <Typography component="h3" variant="h4">Aplicabilidade e lacunas por objetivo</Typography>
      {rows(data.profiles).map((profile, index) => <Box key={index} sx={{ borderLeft: '2px solid', borderColor: 'divider', pl: 2 }}><ReadableFields data={profile} /></Box>)}
    </> : artifact.kind === 'evaluation_protocol' ? <>
      <Typography component="h3" variant="h4">Protocolo público, definido antes da execução</Typography>
      <ReadableFields data={object(data.protocol)} />
      <Typography variant="body2">Quantidade de casos protegidos: {text(data.case_count)}</Typography>
      <Alert severity="info">Os casos e as respostas não fazem parte desta leitura pública. Somente o custodiante pode abri-los na aba de custódia.</Alert>
    </> : <>
      <Typography component="h3" variant="h4">Políticas de prescrição</Typography>
      <ReadableFields data={object(data.policies)} />
      <Divider /><Typography component="h3" variant="h4">Execução e informações necessárias</Typography>
      <ReadableFields data={object(data.execution)} />
      <Divider /><Typography component="h3" variant="h4">Contabilização do treino</Typography>
      <ReadableFields data={object(data.accounting)} />
    </>}
  </Stack>
}
