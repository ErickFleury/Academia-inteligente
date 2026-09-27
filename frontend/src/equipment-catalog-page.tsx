import { Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { ClientShell, PublicShell } from './components/application-shell'
import { EquipmentPhoto } from './components/equipment-presentation'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getEquipmentCatalog, type EquipmentCatalogItem } from './equipment'

type EquipmentCatalogPageProps = { onSignOut?: () => void; showClientNavigation?: boolean }
const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR')
const quantity = (item: EquipmentCatalogItem) => `${item.active_quantity} ${item.active_quantity === 1 ? 'unidade ativa' : 'unidades ativas'}`
export function EquipmentCatalogPage({ onSignOut, showClientNavigation = false }: EquipmentCatalogPageProps) {
  const [items, setItems] = useState<EquipmentCatalogItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<EquipmentCatalogItem | null>(null)
  const [reload, setReload] = useState(0)
  useEffect(() => {
    let active = true
    setError(null); setItems(null)
    void getEquipmentCatalog().then((value) => { if (active) setItems(value) }).catch((reason: unknown) => {
      if (active) { setError(reason instanceof Error ? reason.message : 'Não foi possível carregar os equipamentos.'); setItems([]) }
    })
    return () => { active = false }
  }, [reload])
  const filtered = (items || []).filter((item) => normalize(item.name).includes(normalize(search)))
  const content = <Stack spacing={3} sx={{ minWidth: 0 }}>
    <PageHeader eyebrow="Explore a academia" title="Conheça nossos equipamentos" description="Encontre os equipamentos que fazem parte da sua rotina de treino." />
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ alignItems: { sm: 'center' }, justifyContent: 'space-between' }}>
      <TextField label="Buscar equipamento" placeholder="Qual equipamento você procura?" value={search} onChange={(event) => setSearch(event.target.value)} sx={{ width: { xs: '100%', sm: 390 } }} />
      {items && !error && <Typography variant="body2" color="text.secondary" aria-live="polite">{filtered.length} {filtered.length === 1 ? 'equipamento no catálogo' : 'equipamentos no catálogo'}</Typography>}
    </Stack>
    <Typography variant="body2" color="text.secondary">As quantidades indicam unidades ativas no inventário; não indicam uso ou disponibilidade no momento.</Typography>
    {error && <Stack spacing={1}><StatusNotice severity="error">{error}</StatusNotice><Box><Button variant="outlined" onClick={() => setReload((old) => old + 1)}>Tentar novamente</Button></Box></Stack>}
    {!items ? <LoadingState label="Carregando equipamentos" /> : !error && !filtered.length ? <EmptyState title={search ? 'Nenhum equipamento encontrado' : 'Nenhum equipamento ativo'} description={search ? 'Experimente outro nome ou limpe a busca para ver o catálogo.' : 'O catálogo será atualizado quando houver equipamentos disponíveis para consulta.'} /> : <Box component="section" aria-label="Catálogo de equipamentos" sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', sm: 'repeat(2, minmax(0, 1fr))', lg: 'repeat(3, minmax(0, 1fr))' }, gap: 2.5 }}>
      {filtered.map((item) => <Card component="article" key={item.id} sx={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', transition: 'border-color 160ms', '&:hover': { borderColor: 'primary.main' } }}>
        <Box sx={{ borderBottom: '1px solid', borderColor: 'divider', position: 'relative' }}><EquipmentPhoto url={item.image_url} name={item.name} height={210} /></Box>
        <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, flex: 1, p: 2.5 }}>
          <Typography component="h2" variant="h3" sx={{ overflowWrap: 'anywhere' }}>{item.name}</Typography>
          <Box><Chip size="small" variant="outlined" label={quantity(item)} /></Box>
          <Typography color="text.secondary" variant="body2" sx={{ overflowWrap: 'anywhere', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{item.description || 'Conheça este equipamento e inclua-o no treino com orientação do instrutor.'}</Typography>
          <Button sx={{ alignSelf: 'flex-start', mt: 'auto', px: 0 }} aria-label={`Ver detalhes de ${item.name}`} onClick={() => setSelected(item)}>Conhecer equipamento →</Button>
        </CardContent>
      </Card>)}
    </Box>}
    <Dialog open={!!selected} onClose={() => setSelected(null)} fullWidth maxWidth="sm" aria-labelledby="catalog-equipment-title"><DialogTitle id="catalog-equipment-title" sx={{ overflowWrap: 'anywhere' }}>{selected?.name}</DialogTitle><DialogContent dividers>{selected && <Stack spacing={2.5}><EquipmentPhoto url={selected.image_url} name={selected.name} height={260} /><Box><Chip variant="outlined" label={quantity(selected)} /></Box><Typography sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{selected.description || 'Peça ao instrutor uma orientação sobre o uso deste equipamento.'}</Typography></Stack>}</DialogContent><DialogActions><Button onClick={() => setSelected(null)}>Fechar detalhes</Button></DialogActions></Dialog>
  </Stack>
  if (showClientNavigation) return <ClientShell onSignOut={onSignOut} showClientNavigation contentMaxWidth="lg">{content}</ClientShell>
  return <PublicShell contentMaxWidth="lg">{content}</PublicShell>
}
