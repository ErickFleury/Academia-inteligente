import { Box, Chip, Stack, Typography } from '@mui/material'
import type { ReviewContent } from '../training-review'

export function TrainingPlanContent({ plan }: { plan: ReviewContent }) {
  return <Stack spacing={3}>
    <Box sx={{ pl: 2, borderLeft: '3px solid', borderColor: 'primary.main' }}>
      <Typography component="h3" variant="overline" color="text.secondary">Objetivo do treino</Typography>
      <Typography sx={{ mt: 0.75, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{plan.objective}</Typography>
    </Box>
    <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
      <Typography component="h3" variant="h3">Sequência de exercícios</Typography>
      <Chip size="small" label={`${plan.items.length} ${plan.items.length === 1 ? 'exercício' : 'exercícios'}`} />
    </Stack>
    <Stack component="ol" spacing={2} sx={{ listStyle: 'none', p: 0, m: 0 }}>
      {plan.items.map((item, index) => <Box component="li" key={index} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2.5, overflow: 'hidden', bgcolor: 'rgba(16,24,27,0.35)' }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', px: { xs: 2, sm: 2.5 }, py: 2, bgcolor: 'action.hover' }}>
          <Box aria-hidden="true" sx={{ color: 'primary.main', fontWeight: 800, fontSize: '1.2rem', minWidth: 36, textAlign: 'center' }}>{String(index + 1).padStart(2, '0')}</Box>
          <Typography component="h4" variant="h4" sx={{ overflowWrap: 'anywhere', minWidth: 0 }}>{item.exercise_name}</Typography>
        </Stack>
        <Stack spacing={2} sx={{ p: { xs: 2, sm: 2.5 } }}>
          <Box component="dl" sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 1.5, m: 0, pb: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
            {[
              ['Séries', String(item.sets)],
              ['Repetições', item.repetitions],
              ['Descanso', `${item.rest_seconds} s`],
            ].map(([label, value]) => <Box key={label} sx={{ minWidth: 0 }}>
              <Typography component="dt" variant="caption" color="text.secondary">{label}</Typography>
              <Typography component="dd" sx={{ m: 0, mt: 0.25, fontWeight: 750, overflowWrap: 'anywhere' }}>{value}</Typography>
            </Box>)}
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">Orientação de carga</Typography>
            <Typography sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.load_guidance}</Typography>
          </Box>
          {item.equipment_requirement && <Box sx={{ borderTop: '1px solid', borderColor: 'divider', pt: 1.5 }}>
            <Typography variant="caption" color="text.secondary">Equipamento registrado</Typography>
            <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>{item.equipment_requirement}</Typography>
          </Box>}
        </Stack>
      </Box>)}
    </Stack>
  </Stack>
}
