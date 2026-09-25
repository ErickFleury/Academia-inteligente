import { Box, Card, CardContent, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { PublicShell } from './components/application-shell'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getEquipmentCatalog, type EquipmentCatalogItem } from './equipment'

export function EquipmentCatalogPage() {
  const [items, setItems] = useState<EquipmentCatalogItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void getEquipmentCatalog()
      .then(setItems)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : 'Não foi possível carregar os equipamentos.')
        setItems([])
      })
  }, [])

  return (
    <PublicShell>
      <Stack spacing={3} sx={{ minWidth: 0 }}>
        <PageHeader
          eyebrow="Equipamentos"
          title="Conheça nossos equipamentos"
          description="Confira os equipamentos ativos no catálogo da academia. As quantidades não indicam uso ou disponibilidade no momento."
        />
        {error && <StatusNotice severity="error">{error}</StatusNotice>}
        {!items ? <LoadingState label="Carregando equipamentos" /> : items.length === 0 ? (
          <EmptyState title="Nenhum equipamento ativo" description="O catálogo será atualizado quando houver equipamentos disponíveis para consulta." />
        ) : (
          <Stack component="section" spacing={2}>
            {items.map((item) => (
              <Card component="article" key={item.id} sx={{ overflow: 'hidden' }}>
                <Stack direction={{ xs: 'column', sm: 'row' }}>
                  {item.image_url && <Box alt={`Imagem de ${item.name}`} component="img" src={item.image_url} sx={{ bgcolor: 'action.hover', height: { xs: 190, sm: 160 }, objectFit: 'cover', width: { xs: '100%', sm: 240 } }} />}
                  <CardContent sx={{ flex: 1, minWidth: 0 }}>
                    <Stack spacing={1}>
                      <Typography component="h2" variant="h3">{item.name}</Typography>
                      <Typography color="primary.main" variant="h4">{item.active_quantity} {item.active_quantity === 1 ? 'unidade ativa' : 'unidades ativas'}</Typography>
                      {item.description && <Typography color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>{item.description}</Typography>}
                    </Stack>
                  </CardContent>
                </Stack>
              </Card>
            ))}
          </Stack>
        )}
      </Stack>
    </PublicShell>
  )
}
