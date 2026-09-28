import { Avatar, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { fetchProfileImage, getProfileConnections, type ProfileConnectionDirection, type ProfileSummary } from '../social'
import { RouterButtonLink } from './router-button-link'
import { EmptyState, LoadingState, StatusNotice } from './ui'

function ConnectionLink({ profile, accessToken, onNavigate }: { profile: ProfileSummary; accessToken: string; onNavigate: () => void }) {
  const [image, setImage] = useState<string | null>(null)
  useEffect(() => {
    setImage(null)
    if (!profile.has_image) return
    let active = true
    let loaded: string | null = null
    void fetchProfileImage(accessToken, profile.id).then((url) => {
      if (active) { loaded = url; setImage(url) } else URL.revokeObjectURL(url)
    }).catch(() => undefined)
    return () => { active = false; if (loaded) URL.revokeObjectURL(loaded) }
  }, [accessToken, profile.id, profile.has_image])
  return <RouterButtonLink to={`/perfis/${profile.id}`} onClick={onNavigate} color="inherit" sx={{ justifyContent: 'flex-start', gap: 1.5, textAlign: 'left', width: '100%', py: 1.25 }}>
    <Avatar src={image ?? undefined} alt="">{(profile.nickname || profile.name).slice(0, 1)}</Avatar>
    <Stack sx={{ minWidth: 0 }}>
      <Typography component="span" sx={{ overflowWrap: 'anywhere', fontWeight: 700 }}>{profile.nickname || profile.name}</Typography>
      {profile.nickname && <Typography component="span" color="text.secondary" variant="body2">{profile.name}</Typography>}
    </Stack>
  </RouterButtonLink>
}

// Mounted per profile/direction so an old request cannot populate another list.
export function ProfileConnectionsDialog({ accessToken, profileId, direction, onClose }: {
  accessToken: string; profileId: string; direction: ProfileConnectionDirection; onClose: () => void
}) {
  const [items, setItems] = useState<ProfileSummary[]>([])
  const [offset, setOffset] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  useEffect(() => {
    let active = true
    setLoading(true); setError(false)
    void getProfileConnections(accessToken, profileId, direction, offset).then((page) => {
      if (!active) return
      setItems((previous) => offset === 0 ? page : [...previous, ...page.filter((item) => !previous.some((old) => old.id === item.id))])
      setHasMore(page.length === 20)
    }).catch(() => {
      if (active) { setError(true); setItems([]); setHasMore(false) }
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [accessToken, profileId, direction, offset, attempt])
  return <Dialog open fullWidth maxWidth="sm" onClose={onClose} aria-labelledby="profile-connections-title">
    <DialogTitle id="profile-connections-title">{direction === 'followers' ? 'Seguidores' : 'Seguindo'}</DialogTitle>
    <DialogContent>
      <Stack spacing={1.5}>
        <Typography color="text.secondary" variant="body2">Somente perfis disponíveis para você são exibidos.</Typography>
        {error && <><StatusNotice severity="error">Não foi possível carregar esta lista. Ela pode estar indisponível para você.</StatusNotice><Button onClick={() => { setOffset(0); setAttempt((value) => value + 1) }}>Tentar novamente</Button></>}
        {!error && !loading && items.length === 0 && <EmptyState title={direction === 'followers' ? 'Nenhum seguidor disponível' : 'Nenhum perfil seguido disponível'} description="Os perfis disponíveis aparecerão aqui." />}
        {items.length > 0 && <Stack component="ul" spacing={0.5} sx={{ m: 0, p: 0, listStyle: 'none' }}>{items.map((profile) => <li key={profile.id}><ConnectionLink profile={profile} accessToken={accessToken} onNavigate={onClose} /></li>)}</Stack>}
        {loading && <LoadingState label="Carregando perfis" />}
        {hasMore && !loading && !error && <Button onClick={() => setOffset(offset + 20)} variant="outlined">Carregar mais</Button>}
      </Stack>
    </DialogContent>
    <DialogActions><Button onClick={onClose}>Fechar</Button></DialogActions>
  </Dialog>
}
