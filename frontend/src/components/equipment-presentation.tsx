import { Box, Chip, Stack, SvgIcon, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { equipmentImageUrl } from '../equipment'

export function EquipmentGlyph() {
  return <SvgIcon aria-hidden="true" sx={{ fontSize: 40 }}><path d="M5 5h3v5h8V5h3v3h2v8h-2v3h-3v-5H8v5H5v-3H3V8h2zm3 7h8v-1H8z" /></SvgIcon>
}
export function EquipmentPhoto({ url, name, token, compact = false, revision = '', height = 190 }: { url: string | null; name: string; token?: string; compact?: boolean; revision?: string; height?: number }) {
  const [source, setSource] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let active = true
    let local: string | null = null
    setSource(null); setFailed(false)
    if (!url) return
    if (url.startsWith('/equipment/admin/') && token) {
      void fetch(equipmentImageUrl(url), { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' })
        .then((response) => { if (!response.ok) throw new Error(); return response.blob() })
        .then((blob) => { if (active) { local = URL.createObjectURL(blob); setSource(local) } })
        .catch(() => { if (active) setFailed(true) })
    } else if (/^(https?:\/\/|blob:|\/[^/\\])/.test(url) && !url.includes('\\')) setSource(equipmentImageUrl(url))
    else setFailed(true)
    return () => { active = false; if (local) URL.revokeObjectURL(local) }
  }, [url, token, revision])
  return <Box sx={{ flexShrink: 0, width: compact ? 72 : '100%', height: compact ? 64 : height, borderRadius: compact ? 2 : 0, overflow: 'hidden', bgcolor: 'action.hover', display: 'grid', placeItems: 'center', color: 'text.secondary' }}>
    {source && !failed ? <Box component="img" src={source} alt={`Imagem de ${name}`} loading="lazy" referrerPolicy="no-referrer" onError={() => setFailed(true)} sx={{ width: '100%', height: '100%', objectFit: 'contain', minHeight: 0 }} /> : <Stack sx={{ alignItems: 'center' }} spacing={1}><EquipmentGlyph />{!compact && <Typography variant="caption">{failed ? 'Imagem indisponível' : 'Foto não cadastrada'}</Typography>}</Stack>}
  </Box>
}
export function EquipmentStats({ items }: { items: Array<{ label: string; value: number; warning?: boolean }> }) {
  return <Box sx={{ display: 'grid', gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))`, border: '1px solid', borderColor: 'divider', borderRadius: 2, overflow: 'hidden', bgcolor: 'background.paper' }}>
    {items.map((item, index) => <Box key={item.label} sx={{ px: { xs: 1.5, sm: 2.5 }, py: 2, borderLeft: index ? '1px solid' : 0, borderColor: 'divider' }}><Typography variant="h3" sx={{ fontSize: { xs: '1.5rem', sm: '1.9rem' }, color: item.warning ? 'warning.main' : 'text.primary' }}>{item.value}</Typography><Typography variant="body2" color="text.secondary">{item.label}</Typography></Box>)}
  </Box>
}
export function InventoryChip({ active }: { active: boolean }) {
  return <Chip size="small" variant="outlined" color={active ? 'success' : 'default'} label={active ? 'Ativo no inventário' : 'Inativo no inventário'} />
}
export function OperationalChip({ state }: { state: 'operational' | 'out_of_order' }) {
  return <Chip size="small" color={state === 'operational' ? 'success' : 'warning'} variant="outlined" label={state === 'operational' ? 'Em funcionamento' : 'Fora de serviço'} />
}
