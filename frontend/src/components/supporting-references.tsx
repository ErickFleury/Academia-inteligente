import { Box, Typography } from '@mui/material'

export type SupportingReference = { passage_id: string; title: string; version: number; location: string }
export function SupportingReferences({ references }: { references?: SupportingReference[] }) {
  if (!references?.length) return null
  return <Box component="ul" aria-label="Referências de apoio" sx={{ pl: 2, mb: 0 }}>
    {references.map((citation) => <Typography component="li" variant="caption" key={citation.passage_id}>
      {citation.title} · versão {citation.version} · {citation.location.replace('page:', 'página ').replace(';passage:', ' · trecho ').replace('text', 'texto')}
    </Typography>)}
  </Box>
}
