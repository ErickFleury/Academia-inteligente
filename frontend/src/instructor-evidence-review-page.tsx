import { Alert, Box, Button, Card, CardContent, Checkbox, Divider, FormControlLabel, MenuItem, Stack, Tab, Tabs, TextField, Typography } from '@mui/material'
import { useEffect, useRef, useState, type FormEvent } from 'react'

import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { EvidenceReviewMaterial, materialKindLabels, reviewMaterialTitle } from './components/evidence-review-material'
import {
  certaintyLabels, EvidenceReviewError, getEvidenceArtifact, getEvidenceSealCases,
  listEvidenceArtifacts, listEvidenceSeals, reviewDecisionLabels, reviewFunctionLabels,
  getEvidenceReadiness, type EvidenceReadiness,
  submitEvidenceJudgment, submitEvidenceSeal,
  type Certainty, type DomainJudgment, type EvidenceArtifact, type EvidenceSeal,
  type JudgmentInput, type OutcomeCertainty, type ReviewDecision, type ReviewFunction,
  type SealCases, type SealInput, type SealedCase,
} from './evidence-review'
import { InstructorShell } from './instructor-shell'

type Props = { accessToken: string; onSignOut: () => void }
const date = (value: string) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
const reviewHelp = {
  scope: 'Informe para quais pessoas, objetivos e situações seu parecer vale e o que ficou fora da análise.',
  method_and_version: 'Identifique o método ou instrumento realmente utilizado e sua versão. Não declare uma avaliação que não realizou.',
  rationale: 'Explique o que sustenta sua decisão, as limitações e as alterações necessárias, quando houver.',
  competence: 'Descreva sua formação e experiência pertinentes ao material avaliado.',
  conflicts: 'Declare vínculos ou interesses relevantes; se não houver, informe isso explicitamente.',
}
// Fixed native textareas avoid repeated layout measurement in long review forms.
const reviewTextAreaSlots = (minLength: number, maxLength: number) => ({ input: { inputComponent: 'textarea' as const }, htmlInput: { rows: 3, minLength, maxLength } })

function ReviewForm({ artifact, busy, onSubmit }: {
  artifact: EvidenceArtifact; busy: boolean; onSubmit: (data: JudgmentInput) => Promise<void>
}) {
  const [fields, setFields] = useState({ scope: '', method_and_version: '', rationale: '', competence: '', conflicts: '' })
  const [reviewFunction, setReviewFunction] = useState<ReviewFunction>('methodological')
  const [decision, setDecision] = useState<ReviewDecision>('changes_requested')
  const [judgments, setJudgments] = useState<DomainJudgment[]>([{ domain: '', judgment: '', source_locator: '' }])
  const [outcomes, setOutcomes] = useState<OutcomeCertainty[]>([{ outcome: '', certainty: 'not_assessed', rationale: '' }])
  const [attested, setAttested] = useState(false)
  const [independent, setIndependent] = useState(false)
  const [reviewDueAt, setReviewDueAt] = useState('')
  const [replacementAttested, setReplacementAttested] = useState(false)
  const [resolves, setResolves] = useState(false)
  const [done, setDone] = useState(false)
  const lock = useRef(false)
  const command = useRef<{ key: string; id: string } | null>(null)
  const previous = artifact.judgments.find((r) => r.can_supersede && r.is_current && r.artifact_sha256 === artifact.sha256)
  const effectiveFunction = previous?.function ?? reviewFunction
  const references = artifact.judgments.filter((r) => r.is_current && r.artifact_sha256 === artifact.sha256 && r.function !== 'adjudicator')
  async function send(event: FormEvent) {
    event.preventDefault()
    if (lock.current || busy || done) return
    const body = {
      ...fields, expected_artifact_sha256: artifact.sha256, function: effectiveFunction,
      decision, judgments, outcomes, personally_performed: attested,
      independent_assessment: independent,
      supersedes_judgment_id: previous?.id ?? null, review_due_at: reviewDueAt || null,
      resolves_judgment_ids: effectiveFunction === 'adjudicator' && resolves ? references.map((r) => r.id) : [],
    }
    const key = JSON.stringify(body)
    if (command.current?.key !== key) command.current = { key, id: crypto.randomUUID() }
    lock.current = true
    try { await onSubmit({ ...body, request_id: command.current.id }); setDone(true) }
    catch { /* The workspace displays controlled feedback and preserves the form. */ }
    finally { lock.current = false }
  }
  if (done) return <StatusNotice severity="success">Parecer registrado nesta versão. A aprovação de políticas e a liberação continuam sendo etapas separadas.</StatusNotice>
  const approvalBlocked = decision === 'approved' && (!artifact.approval_ready || !reviewDueAt || !independent || outcomes.some((o) => o.certainty === 'not_assessed'))
  return <Stack component="form" aria-label="Registrar parecer" spacing={2} onSubmit={(event) => void send(event)}>
    <Typography component="h3" variant="h4">Registrar meu parecer</Typography>
    <Alert severity="info">{effectiveFunction === 'methodological' ? 'Na revisão metodológica, avalie como a evidência foi produzida, suas limitações e a certeza por desfecho. Para julgar um estudo, os trechos usados no RAG podem ser insuficientes: consulte o documento completo.' : effectiveFunction === 'professional' ? 'Na revisão profissional, avalie a aplicação prática: população, objetivos, doses, restrições, viabilidade e limites. Confira a recomendação e suas fontes antes de decidir.' : 'Na resolução de divergência, leia os dois pareceres e as evidências e explique quais pontos foram resolvidos e por quê.'}</Alert>
    <Typography variant="body2">Cada pessoa mantém uma avaliação por versão. Uma substituição preserva o histórico; as funções independentes precisam de pessoas distintas. Não inclua dados de alunos.</Typography>
    {previous && <FormControlLabel control={<Checkbox checked={replacementAttested} disabled={busy} onChange={(_, checked) => { setReplacementAttested(checked); setReviewFunction(previous.function) }} />} label="Estou substituindo meu parecer anterior, preservando seu histórico e a mesma função de revisão" />}
    <TextField select label="Função da revisão" value={previous?.function ?? reviewFunction} slotProps={{ select: { renderValue: (value) => reviewFunctionLabels[value as ReviewFunction] } }} onChange={(e) => setReviewFunction(e.target.value as ReviewFunction)} disabled={busy || !!previous}>
      {Object.entries(reviewFunctionLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
    </TextField>
    <TextField label="Prazo para nova revisão" type="date" required={decision === 'approved'} value={reviewDueAt} disabled={busy} onChange={(e) => setReviewDueAt(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
    <TextField select label="Decisão do parecer" value={decision} slotProps={{ select: { renderValue: (value) => reviewDecisionLabels[value as ReviewDecision] } }} onChange={(e) => setDecision(e.target.value as ReviewDecision)} disabled={busy}>
      {Object.entries(reviewDecisionLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
    </TextField>
    {([
      ['scope', 'Escopo e população avaliados', 3, 4000], ['method_and_version', 'Método de avaliação e versão', 3, 4000],
      ['rationale', 'Fundamentação do parecer', 20, 8000], ['competence', 'Qualificação e experiência para esta revisão', 3, 4000],
      ['conflicts', 'Declaração de conflitos de interesse', 3, 4000],
    ] as const).map(([key, label, minLength, maxLength]) => <TextField key={key} label={label} helperText={reviewHelp[key]} value={fields[key]} onChange={(e) => setFields((old) => ({ ...old, [key]: e.target.value }))} required multiline disabled={busy} slotProps={reviewTextAreaSlots(minLength, maxLength)} />)}
    {judgments.map((item, index) => <Stack key={index} spacing={1} component="fieldset" sx={{ border: '1px solid', borderColor: 'divider', p: 2, minWidth: 0 }}>
      <Typography component="legend">Julgamento {index + 1}</Typography>
      {([['domain', 'Domínio avaliado'], ['judgment', 'Julgamento do domínio'], ['source_locator', 'Localização da evidência']] as const).map(([key, label]) => <TextField key={key} label={`${label} ${index + 1}`} required multiline disabled={busy} value={item[key]} onChange={(e) => setJudgments((old) => old.map((row, i) => i === index ? { ...row, [key]: e.target.value } : row))} slotProps={reviewTextAreaSlots(3, 4000)} />)}
    </Stack>)}
    <Button disabled={busy || judgments.length >= 100} onClick={() => setJudgments((old) => [...old, { domain: '', judgment: '', source_locator: '' }])}>Adicionar julgamento</Button>
    <Typography variant="body2">Em cada julgamento, indique o aspecto avaliado, sua conclusão e a página, tabela, seção ou identificador do trecho que permite conferir a evidência. Para cada desfecho, explique o grau de certeza atribuído; não o escolha apenas por haver uma citação.</Typography>
    {outcomes.map((item, index) => <Stack key={index} spacing={1} component="fieldset" sx={{ border: '1px solid', borderColor: 'divider', p: 2, minWidth: 0 }}>
      <Typography component="legend">Certeza por desfecho {index + 1}</Typography>
      <TextField label={`Desfecho avaliado ${index + 1}`} required disabled={busy} value={item.outcome} onChange={(e) => setOutcomes((old) => old.map((row, i) => i === index ? { ...row, outcome: e.target.value } : row))} slotProps={{ htmlInput: { minLength: 3, maxLength: 4000 } }} />
      <TextField select label={`Certeza do desfecho ${index + 1}`} disabled={busy} value={item.certainty} slotProps={{ select: { renderValue: (value) => certaintyLabels[value as Certainty] } }} onChange={(e) => setOutcomes((old) => old.map((row, i) => i === index ? { ...row, certainty: e.target.value as Certainty } : row))}>
        {Object.entries(certaintyLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
      </TextField>
      <TextField label={`Justificativa da certeza ${index + 1}`} required multiline disabled={busy} value={item.rationale} onChange={(e) => setOutcomes((old) => old.map((row, i) => i === index ? { ...row, rationale: e.target.value } : row))} slotProps={reviewTextAreaSlots(3, 4000)} />
    </Stack>)}
    <Button disabled={busy || outcomes.length >= 100} onClick={() => setOutcomes((old) => [...old, { outcome: '', certainty: 'not_assessed', rationale: '' }])}>Adicionar desfecho</Button>
    {effectiveFunction === 'adjudicator' && <FormControlLabel control={<Checkbox checked={resolves} disabled={busy} onChange={(_, checked) => setResolves(checked)} />} label="Este parecer resolve a divergência entre os pareceres metodológico e profissional exibidos para esta versão" />}
    <FormControlLabel control={<Checkbox checked={attested} disabled={busy} onChange={(_, checked) => setAttested(checked)} />} label="Declaro que realizei pessoalmente esta avaliação e conferi as fontes e a versão exibida" />
    <FormControlLabel control={<Checkbox checked={independent} disabled={busy} onChange={(_, checked) => setIndependent(checked)} />} label="Declaro a independência desta avaliação em relação ao desenvolvimento e ao ajuste do sistema" />
    {approvalBlocked && <Alert severity="info">A aprovação exige um artefato completo, a avaliação explícita da certeza e um prazo futuro para nova revisão. Você pode registrar as alterações necessárias.</Alert>}
    <Button type="submit" variant="contained" disabled={busy || !attested || approvalBlocked || (!!previous && !replacementAttested) || (effectiveFunction === 'adjudicator' && !resolves)}>{busy ? 'Registrando parecer…' : 'Registrar parecer desta versão'}</Button>
  </Stack>
}

function SealForm({ artifacts, busy, onSubmit }: { artifacts: EvidenceArtifact[]; busy: boolean; onSubmit: (data: SealInput) => Promise<void> }) {
  const [artifactId, setArtifactId] = useState('')
  const [protocol, setProtocol] = useState({ title: '', scope: '', methods: '', decision_thresholds: '', repeat_count: '', maximum_writer_calls: '', maximum_runtime_seconds: '' })
  const [cases, setCases] = useState<SealedCase[]>([{ case_id: '', cohort: '', scenario: '', reference_judgment: '', critical: false }])
  const [declarations, setDeclarations] = useState({ synthetic_only: false, independent_and_unexposed: false, understands_no_release: false })
  const [done, setDone] = useState(false)
  const command = useRef<{ key: string; id: string } | null>(null)
  const lock = useRef(false)
  async function send(event: FormEvent) {
    event.preventDefault()
    if (busy || lock.current) return
    const artifact = artifacts.find((item) => item.id === artifactId)
    if (!artifact) return
    const body = {
      artifact_hashes: { [artifact.id]: artifact.sha256 },
      protocol: { ...protocol, repeat_count: Number(protocol.repeat_count), maximum_writer_calls: Number(protocol.maximum_writer_calls), maximum_runtime_seconds: Number(protocol.maximum_runtime_seconds) },
      cases, ...declarations,
    }
    const key = JSON.stringify(body)
    if (command.current?.key !== key) command.current = { key, id: crypto.randomUUID() }
    lock.current = true
    try {
      await onSubmit({ ...body, request_id: command.current.id })
      setCases([]); setDone(true)
    } catch { /* Preserve entered cases for an intentional retry. */ }
    finally { lock.current = false }
  }
  if (done) return <StatusNotice severity="success">Custódia registrada. Os casos ficaram restritos à sua conta; a avaliação e a liberação ainda precisam ser concluídas.</StatusNotice>
  return <Stack component="form" aria-label="Registrar custódia da avaliação" spacing={2} onSubmit={(event) => void send(event)}>
    <Typography component="h3" variant="h4">Registrar custódia de uma avaliação</Typography>
    <Alert severity="info">Use somente casos sintéticos. Os demais instrutores verão o protocolo e os hashes, sem os casos nem as respostas. Uma alteração exige outro registro de custódia.</Alert>
    <TextField select required label="Artefato de referência" value={artifactId} slotProps={{ select: { renderValue: (value) => { const item = artifacts.find((entry) => entry.id === value); return item ? reviewMaterialTitle(item) : '' } } }} disabled={busy} onChange={(e) => setArtifactId(e.target.value)}>
      {artifacts.map((item) => <MenuItem key={item.id} value={item.id} sx={{ whiteSpace: 'normal', maxWidth: '80vw' }}>{reviewMaterialTitle(item)}</MenuItem>)}
    </TextField>
    {([
      ['title', 'Título da avaliação', 5, 200], ['scope', 'Perfis e objetivos da avaliação', 3, 4000],
      ['methods', 'Métodos e partições da avaliação', 3, 4000], ['decision_thresholds', 'Critérios e limites de aprovação definidos antes da execução', 20, 8000],
    ] as const).map(([key, label, minLength, maxLength]) => <TextField key={key} label={label} required multiline disabled={busy} value={protocol[key]} onChange={(e) => setProtocol((old) => ({ ...old, [key]: e.target.value }))} slotProps={reviewTextAreaSlots(minLength, maxLength)} />)}
    {([
      ['repeat_count', 'Repetições por caso'], ['maximum_writer_calls', 'Limite total de chamadas ao modelo'], ['maximum_runtime_seconds', 'Limite total de execução em segundos'],
    ] as const).map(([key, label]) => <TextField key={key} label={label} required type="number" disabled={busy} value={protocol[key]} onChange={(e) => setProtocol((old) => ({ ...old, [key]: e.target.value }))} slotProps={{ htmlInput: { min: 1, step: 1 } }} />)}
    {cases.map((item, index) => <Stack component="fieldset" key={index} spacing={1} sx={{ border: '1px solid', borderColor: 'divider', p: 2, minWidth: 0 }}>
      <Typography component="legend">Caso privado {index + 1}</Typography>
      {([['case_id', 'Identificador do caso', 1, 100], ['cohort', 'Perfil sintético', 1, 200], ['scenario', 'Descrição do caso sintético', 3, 4000], ['reference_judgment', 'Julgamento de referência privado', 3, 4000]] as const).map(([key, label, minLength, maxLength]) => <TextField key={key} required multiline disabled={busy} label={`${label} ${index + 1}`} value={item[key]} onChange={(e) => setCases((old) => old.map((row, i) => i === index ? { ...row, [key]: e.target.value } : row))} slotProps={reviewTextAreaSlots(minLength, maxLength)} />)}
      <FormControlLabel control={<Checkbox checked={item.critical} disabled={busy} onChange={(_, checked) => setCases((old) => old.map((row, i) => i === index ? { ...row, critical: checked } : row))} />} label={`Caso crítico ${index + 1}`} />
      <Button disabled={busy || cases.length === 1} onClick={() => setCases((old) => old.filter((_, i) => i !== index))}>Remover caso {index + 1}</Button>
    </Stack>)}
    <Button disabled={busy || cases.length >= 500} onClick={() => setCases((old) => [...old, { case_id: '', cohort: '', scenario: '', reference_judgment: '', critical: false }])}>Adicionar caso privado</Button>
    {([
      ['synthetic_only', 'Confirmo que todos os casos são sintéticos e não contêm dados reais de alunos'],
      ['independent_and_unexposed', 'Confirmo a independência da avaliação e que os casos e respostas não foram expostos a quem implementou ou ajustou o sistema'],
      ['understands_no_release', 'Entendo que registrar a custódia não executa a avaliação nem libera perfis ou planos'],
    ] as const).map(([key, label]) => <FormControlLabel key={key} label={label} control={<Checkbox checked={declarations[key]} disabled={busy} onChange={(_, checked) => setDeclarations((old) => ({ ...old, [key]: checked }))} />} />)}
    <Button type="submit" variant="contained" disabled={busy || !artifactId || !Object.values(declarations).every(Boolean)}>{busy ? 'Registrando custódia…' : 'Registrar custódia e proteger casos'}</Button>
  </Stack>
}

function Workspace({ accessToken, onSignOut }: Props) {
  const [artifacts, setArtifacts] = useState<EvidenceArtifact[]>([])
  const [seals, setSeals] = useState<EvidenceSeal[]>([])
  const [selected, setSelected] = useState<EvidenceArtifact | null>(null)
  const [readiness, setReadiness] = useState<EvidenceReadiness | null>(null)
  const [materialKind, setMaterialKind] = useState<EvidenceArtifact['kind'] | 'all'>('all')
  const [privateCases, setPrivateCases] = useState<SealCases | null>(null)
  const [tab, setTab] = useState<'artifacts' | 'custody'>('artifacts')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const alive = useRef(true)
  const working = useRef(false)
  const failure = (reason: unknown) => {
    if (!alive.current) return
    setError(reason instanceof Error ? reason.message : 'Não foi possível carregar as evidências.')
    if (reason instanceof EvidenceReviewError && reason.status === 401) onSignOut()
  }
  useEffect(() => {
    let active = true
    alive.current = true
    setLoading(true); setError(null); setSelected(null); setPrivateCases(null); setReadiness(null)
    void Promise.all([listEvidenceArtifacts(accessToken), listEvidenceSeals(accessToken)])
      .then(([nextArtifacts, nextSeals]) => { if (active) { setArtifacts(nextArtifacts); setSeals(nextSeals) } })
      .catch((reason: unknown) => { if (active) failure(reason) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false; alive.current = false }
  }, [accessToken, reload])
  async function perform(operation: () => Promise<void>) {
    if (working.current) throw new Error('Aguarde a operação atual.')
    working.current = true; setBusy(true); setError(null)
    try { await operation() }
    catch (reason) { failure(reason); throw reason }
    finally { working.current = false; if (alive.current) setBusy(false) }
  }
  async function openArtifact(id: string) {
    try { await perform(async () => { const next = await getEvidenceArtifact(accessToken, id); if (alive.current) setSelected(next) }) }
    catch { /* Controlled feedback is displayed above the workspace. */ }
  }
  return <InstructorShell onSignOut={onSignOut} contentMaxWidth="lg"><Stack spacing={3} sx={{ minWidth: 0, overflowWrap: 'anywhere' }}>
    <PageHeader title="Revisão de evidências" eyebrow="Responsabilidade profissional" description="Registre avaliações das fontes e dos contratos de prescrição, com autoria e versão, e proteja os casos da avaliação independente." action={<Button disabled={loading || busy} onClick={() => setReload((value) => value + 1)}>Recarregar registros</Button>} />
    <StatusNotice severity="info">O RAG assistido pode funcionar por autorização do proprietário, sem parecer ou avaliação independente. Os registros abaixo permitem avaliações opcionais. Cada ficha continua sujeita à revisão do instrutor antes da ativação.</StatusNotice>
    {error && <StatusNotice severity="error">{error}</StatusNotice>}
    <Button disabled={loading || busy} onClick={() => void perform(async () => { const next = await getEvidenceReadiness(accessToken); if (alive.current) setReadiness(next) }).catch(() => {})}>Consultar prontidão dos contratos</Button>
    {readiness && <Stack spacing={1} component="section" aria-label="Prontidão dos contratos">
      <Typography variant="h4" component="h2">Prontidão para prescrição</Typography>
      {readiness.owner_rag?.enabled && readiness.owner_rag.authorized && <Alert severity="info">RAG assistido habilitado por decisão do proprietário. Sem parecer profissional ou avaliação independente. As políticas de prescrição com verificação completa são uma etapa separada.</Alert>}
      <Typography>{readiness.rules.filter((rule) => rule.owner_accepted).length} regras com aprovação do proprietário. A autorização de consulta não completa contratos nem libera perfis automaticamente.</Typography>
      {readiness.missing_items.map((item) => <Alert key={item} severity="warning">{item}</Alert>)}
      <Typography>{readiness.profiles.filter((profile) => profile.compiled_policy_ids.length > 0).length} famílias com políticas compiladas; {readiness.enabled_cohorts.length} perfis liberados.</Typography>
    </Stack>}
    <Tabs value={tab} variant="scrollable" scrollButtons="auto" allowScrollButtonsMobile onChange={(_, value) => { setTab(value); setPrivateCases(null) }} aria-label="Etapas da revisão de evidências">
      <Tab label="Artefatos e pareceres" value="artifacts" id="evidencias-artefatos" aria-controls="evidencias-painel-artefatos" />
      <Tab label="Custódia da avaliação" value="custody" id="evidencias-custodia" aria-controls="evidencias-painel-custodia" />
    </Tabs>
    {loading ? <LoadingState label="Carregando artefatos e registros de revisão" /> : tab === 'artifacts' ? <Stack spacing={2} role="tabpanel" id="evidencias-painel-artefatos" aria-labelledby="evidencias-artefatos">
      <Typography component="h2" variant="h3">Escolha o material que vai avaliar</Typography>
      <Typography variant="body2">Fontes são os documentos de consulta. Regras propostas descrevem como usar a evidência no treino. Políticas reúnem as regras e os contratos de execução. Protocolos definem como a avaliação independente será realizada.</Typography>
      <TextField select label="Tipo de material" value={materialKind} disabled={busy} slotProps={{ select: { renderValue: (value) => value === 'all' ? 'Todos os materiais' : materialKindLabels[value as EvidenceArtifact['kind']] } }} onChange={(e) => { setMaterialKind(e.target.value as typeof materialKind); setSelected(null) }}>
        <MenuItem value="all">Todos os materiais</MenuItem>
        {Object.entries(materialKindLabels).map(([kind, label]) => <MenuItem key={kind} value={kind}>{label} ({artifacts.filter((item) => item.kind === kind).length})</MenuItem>)}
      </TextField>
      {materialKind === 'evaluation_protocol' && !artifacts.some((item) => item.kind === 'evaluation_protocol') && <Alert severity="info">Nenhum protocolo de avaliação foi cadastrado. O responsável deve registrá-lo em Custódia da avaliação antes de ele aparecer para revisão.</Alert>}
      <TextField select label="Artefato para revisão" value={selected?.id ?? ''} slotProps={{ select: { renderValue: () => selected ? reviewMaterialTitle(selected) : '' } }} disabled={busy} onChange={(e) => void openArtifact(e.target.value)} fullWidth>
        {artifacts.filter((item) => materialKind === 'all' || item.kind === materialKind).map((item) => <MenuItem key={item.id} value={item.id} sx={{ whiteSpace: 'normal', maxWidth: '80vw' }}>{reviewMaterialTitle(item)}</MenuItem>)}
      </TextField>
      {!selected ? <EmptyState title="Selecione uma fonte ou contrato" description="Confira o conteúdo e a versão antes de registrar seu parecer." /> : <Card><CardContent><Stack spacing={3}>
        <Typography component="h2" variant="h3">{reviewMaterialTitle(selected)}</Typography>
        <Typography variant="subtitle2">{materialKindLabels[selected.kind]}</Typography>
        {selected.owner_approval && <Alert severity="info">Aprovado por decisão do proprietário em {new Intl.DateTimeFormat('pt-BR').format(new Date(selected.owner_approval.decided_on + 'T12:00:00'))}. Sem parecer profissional. Licenças, aplicabilidade e validação técnica continuam obrigatórias.</Alert>}
        {selected.kind === 'prescription_bundle' && <Typography variant="caption">O identificador vincula o conteúdo das políticas e contratos. Situação de aprovação, referências dos pareceres e prazos ficam registrados separadamente.</Typography>}
        <Alert severity={selected.independence_complete ? 'info' : 'warning'}>{selected.independence_complete ? 'Pareceres independentes registrados para esta versão. A liberação continua pendente.' : 'A revisão independente desta versão ainda não está concluída.'}</Alert>
        {selected.missing_items.map((item) => <Alert key={item} severity="warning">{item}</Alert>)}
        <EvidenceReviewMaterial artifact={selected} />
        <Box component="details"><Typography component="summary" sx={{ cursor: 'pointer', fontWeight: 700, minHeight: 44 }}>Dados técnicos da versão (opcional)</Typography>
          <Typography variant="body2">O formulário abaixo se refere ao material apresentado acima. Não é necessário interpretar o JSON para registrar o parecer.</Typography>
          <Typography variant="caption" sx={{ overflowWrap: 'anywhere' }}>Identificador da versão: {selected.sha256}</Typography>
          {selected.sections.map((section, index) => <Box key={index} sx={{ mt: 1 }}><Typography variant="subtitle2">{section.label}</Typography><Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{section.text}</Typography></Box>)}
          {selected.content && <Box component="pre" tabIndex={0} sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', fontSize: '0.75rem', maxHeight: 500, overflowY: 'auto' }}>{JSON.stringify(selected.content, null, 2)}</Box>}
        </Box>
        <Stack spacing={2} component="section" aria-label="Pareceres registrados">
          <Typography component="h3" variant="h4">Pareceres recentes</Typography>
          {!selected.judgments.length && <Typography>Nenhum parecer registrado para este artefato.</Typography>}
          {selected.judgments.map((record) => <Box key={record.id} sx={{ borderLeft: '2px solid', borderColor: 'divider', pl: 2 }}>
            <Typography variant="subtitle2">{record.reviewer_name} · {reviewFunctionLabels[record.function]}</Typography>
            <Typography variant="body2">{reviewDecisionLabels[record.decision]} · {date(record.created_at)}</Typography>
            {record.artifact_sha256 !== selected.sha256 && <Typography variant="caption">Parecer de uma versão anterior.</Typography>}
            {!record.is_current && <Typography variant="caption">Parecer substituído, preservado no histórico.</Typography>}
            {record.assessment.review_due_at && <Typography variant="caption">Prazo de revisão: {new Intl.DateTimeFormat('pt-BR').format(new Date(record.assessment.review_due_at + 'T12:00:00'))}</Typography>}
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{record.assessment.rationale}</Typography>
            <Box component="details"><Typography component="summary" sx={{ cursor: 'pointer' }}>Consultar fundamentação do parecer</Typography>
              <Stack spacing={1} sx={{ mt: 1 }}>
                <Typography variant="body2">Escopo: {record.assessment.scope}</Typography>
                <Typography variant="body2">Método e versão: {record.assessment.method_and_version}</Typography>
                <Typography variant="body2">Qualificação declarada: {record.assessment.competence}</Typography>
                <Typography variant="body2">Conflitos declarados: {record.assessment.conflicts}</Typography>
                {record.assessment.judgments.map((item, index) => <Typography variant="body2" key={index}>{item.domain}: {item.judgment} · Localização: {item.source_locator}</Typography>)}
                {record.assessment.outcomes.map((item, index) => <Typography variant="body2" key={index}>{item.outcome} · Certeza: {certaintyLabels[item.certainty]} · {item.rationale}</Typography>)}
                <Typography variant="caption" sx={{ overflowWrap: 'anywhere' }}>Versão avaliada: {record.artifact_sha256}</Typography>
                <Box component="details"><Typography component="summary" sx={{ cursor: 'pointer' }}>Consultar referência verificável para o contrato</Typography><Box component="pre" tabIndex={0} sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', fontSize: '0.75rem' }}>{JSON.stringify(record.human_review_record, null, 2)}</Box></Box>
              </Stack>
            </Box>
          </Box>)}
        </Stack>
        <Divider />
        <ReviewForm key={`${selected.id}:${selected.sha256}`} artifact={selected} busy={busy} onSubmit={(data) => perform(async () => {
          await submitEvidenceJudgment(accessToken, selected.id, data)
          const next = await getEvidenceArtifact(accessToken, selected.id)
          if (alive.current) setSelected(next)
        })} />
      </Stack></CardContent></Card>}
    </Stack> : <Stack spacing={3} role="tabpanel" id="evidencias-painel-custodia" aria-labelledby="evidencias-custodia">
      <Stack spacing={2} component="section" aria-label="Registros de custódia">
        <Typography component="h2" variant="h3">Custódias registradas</Typography>
        {!seals.length && <Typography>Nenhuma custódia registrada.</Typography>}
        {seals.map((item) => <Card key={item.id}><CardContent><Stack spacing={1}>
          <Typography component="h3" variant="h4">{item.protocol.title}</Typography>
          <Typography variant="body2">Responsável: {item.custodian_name} · {date(item.created_at)} · {item.case_count} casos</Typography>
          <Typography variant="body2">Avaliação e liberação pendentes.</Typography>
          <Typography variant="caption" sx={{ overflowWrap: 'anywhere' }}>Hash dos casos protegidos: {item.payload_sha256}</Typography>
          {item.can_read_cases ? <Button disabled={busy} onClick={() => void perform(async () => { const data = await getEvidenceSealCases(accessToken, item.id); if (alive.current) setPrivateCases(data) }).catch(() => undefined)}>Abrir casos sob minha custódia: {item.protocol.title}</Button> : <Typography variant="body2">Casos e respostas restritos à conta do responsável.</Typography>}
        </Stack></CardContent></Card>)}
      </Stack>
      {privateCases && <Card component="section" aria-label="Casos privados sob minha custódia"><CardContent><Stack spacing={2}>
        <Button onClick={() => setPrivateCases(null)}>Fechar casos privados</Button>
        {privateCases.cases.map((item) => <Box key={item.case_id}><Typography component="h3" variant="h4">Caso {item.case_id}</Typography><Typography>Perfil: {item.cohort} · {item.critical ? 'Caso crítico' : 'Caso não crítico'}</Typography><Typography sx={{ whiteSpace: 'pre-wrap' }}>{item.scenario}</Typography><Typography sx={{ whiteSpace: 'pre-wrap' }}>Referência privada: {item.reference_judgment}</Typography></Box>)}
      </Stack></CardContent></Card>}
      <Card><CardContent><SealForm artifacts={artifacts} busy={busy} onSubmit={(data) => perform(async () => {
        await submitEvidenceSeal(accessToken, data)
        const [nextSeals, nextArtifacts] = await Promise.all([listEvidenceSeals(accessToken), listEvidenceArtifacts(accessToken)])
        if (alive.current) { setSeals(nextSeals); setArtifacts(nextArtifacts) }
      })} /></CardContent></Card>
    </Stack>}
  </Stack></InstructorShell>
}

export function InstructorEvidenceReviewPage(props: Props) {
  const [scope, setScope] = useState({ token: props.accessToken, generation: 0 })
  if (scope.token !== props.accessToken) setScope({ token: props.accessToken, generation: scope.generation + 1 })
  return <Workspace key={scope.generation} {...props} />
}
