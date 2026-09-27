import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'

import { biometricMessage } from '../biometrics'
import { LoadingState, StatusNotice } from './ui'

type Props = { open: boolean; onClose: () => void; onCapture: (image: Blob) => Promise<void>; title?: string }

export function WebcamCapture({ open, onClose, onCapture, title = 'Captura facial' }: Props) {
  const video = useRef<HTMLVideoElement>(null)
  const stream = useRef<MediaStream | null>(null)
  const taking = useRef(false)
  const [ready, setReady] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    let canceled = false
    setReady(false); setError(null)
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('A câmera precisa de uma conexão HTTPS ou localhost e de um navegador compatível.')
      return
    }
    void navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false }).then(async (camera) => {
      if (canceled) { camera.getTracks().forEach((track) => track.stop()); return }
      stream.current = camera
      if (video.current) { video.current.srcObject = camera; await video.current.play() }
    }).catch((reason: unknown) => {
      if (canceled) return
      setError(reason instanceof DOMException && reason.name === 'NotAllowedError'
        ? 'Permita o uso da câmera no navegador e abra a captura novamente.'
        : 'Não foi possível abrir a câmera. Confira a conexão e se outro aplicativo está usando a webcam.')
    })
    return () => { canceled = true; stream.current?.getTracks().forEach((track) => track.stop()); stream.current = null }
  }, [open])

  async function capture() {
    const camera = video.current
    if (!camera || taking.current || !ready) return
    taking.current = true; setBusy(true); setError(null)
    const canvas = document.createElement('canvas')
    try {
      const scale = Math.min(1, 1920 / Math.max(camera.videoWidth, camera.videoHeight))
      canvas.width = Math.round(camera.videoWidth * scale); canvas.height = Math.round(camera.videoHeight * scale)
      const context = canvas.getContext('2d')
      if (!context || !canvas.width || !canvas.height) throw new Error('capture_invalid')
      context.drawImage(camera, 0, 0, canvas.width, canvas.height)
      const image = await new Promise<Blob>((resolve, reject) => canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error('capture_invalid')), 'image/jpeg', 0.9))
      await onCapture(image)
      onClose()
    } catch (reason) { setError(biometricMessage(reason)) }
    finally { canvas.width = 0; canvas.height = 0; taking.current = false; setBusy(false) }
  }

  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm" aria-labelledby="webcam-capture-title">
    <DialogTitle id="webcam-capture-title">{title}</DialogTitle>
    <DialogContent><Stack spacing={2}>
      <Typography>Olhe para a câmera, com boa iluminação e apenas um rosto no enquadramento.</Typography>
      <Box component="video" ref={video} autoPlay muted playsInline onLoadedData={() => setReady(true)} aria-label="Prévia ao vivo da câmera" sx={{ width: '100%', aspectRatio: '16 / 9', objectFit: 'contain', bgcolor: 'common.black', borderRadius: 2 }} />
      <Box aria-live="polite">{busy ? <LoadingState label="Processando captura facial" /> : !ready && !error ? <LoadingState label="Abrindo câmera" /> : null}{error && <StatusNotice severity="error">{error}</StatusNotice>}</Box>
    </Stack></DialogContent>
    <DialogActions><Button onClick={onClose}>Fechar câmera</Button><Button disabled={!ready || busy} variant="contained" onClick={() => void capture()}>{busy ? 'Processando...' : 'Capturar rosto'}</Button></DialogActions>
  </Dialog>
}
