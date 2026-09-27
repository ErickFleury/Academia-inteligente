import { Box, Button, Container, Drawer, IconButton, Stack, Toolbar, Typography } from '@mui/material'
import { useState, type ReactNode } from 'react'

import { RouterButtonLink } from './components/router-button-link'

const links = [
  ['Feed', '/instrutor/feed'], ['Planos pendentes', '/instrutor/planos-pendentes'], ['Meus planos', '/instrutor/meus-planos'], ['Todos os planos', '/instrutor/todos-os-planos'], ['Clientes', '/instrutor/clientes'], ['Equipamentos', '/instrutor/equipamentos'], ['Perfil', '/instrutor/perfil'],
] as const
function Navigation({ compact, close }: { compact?: boolean; close?: () => void }) {
  const path = window.location.pathname
  return <Stack component="nav" aria-label="Navegação da área do instrutor" direction={compact ? 'column' : 'row'} spacing={0.5}>{links.map(([label, to]) => <RouterButtonLink aria-current={path === to ? 'page' : undefined} color={path === to ? 'primary' : 'inherit'} key={to} onClick={close} sx={compact ? { justifyContent: 'flex-start', width: '100%' } : undefined} to={to} variant={path === to ? 'contained' : 'text'}>{label}</RouterButtonLink>)}</Stack>
}
export function InstructorShell({ children, onSignOut }: { children: ReactNode; onSignOut: () => void }) {
  const [open, setOpen] = useState(false)
  return <Box sx={{ minHeight: '100vh', background: 'linear-gradient(160deg, #10181B 0%, #162427 52%, #10181B 100%)' }}><Box sx={{ display: { xs: 'block', md: 'none' }, borderBottom: '1px solid', borderColor: 'divider', position: 'sticky', top: 0, zIndex: 'appBar' }}><Toolbar><IconButton aria-label="Abrir navegação" onClick={() => setOpen(true)}>☰</IconButton><Typography sx={{ fontWeight: 800, ml: 1 }}>Academia Inteligente</Typography></Toolbar></Box><Drawer anchor="left" onClose={() => setOpen(false)} open={open}><Box sx={{ p: 2, width: 'min(82vw, 300px)' }}><Stack spacing={2}><Button onClick={() => setOpen(false)}>Fechar navegação</Button><Navigation compact close={() => setOpen(false)} /><Button onClick={onSignOut}>Sair</Button></Stack></Box></Drawer><Box sx={{ display: { md: 'block', xs: 'none' }, borderBottom: '1px solid', borderColor: 'divider' }}><Container maxWidth="xl"><Stack direction="row" sx={{ alignItems: 'center', minHeight: 72 }}><Typography sx={{ fontWeight: 800, mr: 3 }}>Academia Inteligente</Typography><Navigation /><Box sx={{ flexGrow: 1 }} /><Button onClick={onSignOut}>Sair</Button></Stack></Container></Box><Container component="main" maxWidth="md" sx={{ py: { xs: 3, sm: 5 } }}>{children}</Container></Box>
}
