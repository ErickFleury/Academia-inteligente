import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { WebcamCapture } from './webcam-capture'

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

test('opens camera on request and stops tracks when closed', async () => {
  const stop = vi.fn()
  const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] })
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia } })
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
  const capture = vi.fn()
  const { rerender } = render(<WebcamCapture open={false} onClose={vi.fn()} onCapture={capture} />)
  expect(getUserMedia).not.toHaveBeenCalled()
  rerender(<WebcamCapture open onClose={vi.fn()} onCapture={capture} />)
  await waitFor(() => expect(getUserMedia).toHaveBeenCalledTimes(1))
  expect(capture).not.toHaveBeenCalled()
  expect(document.querySelector('input[type="file"]')).toBeNull()
  rerender(<WebcamCapture open={false} onClose={vi.fn()} onCapture={capture} />)
  await waitFor(() => expect(stop).toHaveBeenCalledTimes(1))
})

test('stops a camera permission request that resolves after unmount', async () => {
  const stop = vi.fn()
  let resolve!: (value: unknown) => void
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: vi.fn().mockReturnValue(new Promise((done) => { resolve = done })) } })
  const { unmount } = render(<WebcamCapture open onClose={vi.fn()} onCapture={vi.fn()} />)
  unmount()
  await act(async () => { resolve({ getTracks: () => [{ stop }] }) })
  expect(stop).toHaveBeenCalledTimes(1)
})

test('captures only on explicit click and blocks duplicate processing', async () => {
  const stop = vi.fn()
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }) } })
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ drawImage: vi.fn() } as unknown as CanvasRenderingContext2D)
  vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((callback) => callback(new Blob(['synthetic'], { type: 'image/jpeg' })))
  let resolve!: () => void
  const capture = vi.fn().mockReturnValue(new Promise<void>((done) => { resolve = done }))
  const close = vi.fn()
  render(<WebcamCapture open onClose={close} onCapture={capture} />)
  const video = screen.getByLabelText('Prévia ao vivo da câmera')
  Object.defineProperty(video, 'videoWidth', { value: 640 })
  Object.defineProperty(video, 'videoHeight', { value: 480 })
  fireEvent.loadedData(video)
  expect(capture).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Capturar rosto' }))
  fireEvent.click(screen.getByRole('button', { name: 'Processando...' }))
  await waitFor(() => expect(capture).toHaveBeenCalledTimes(1))
  expect(screen.getByRole('button', { name: 'Processando...' })).toBeDisabled()
  await act(async () => { resolve() })
  expect(close).toHaveBeenCalledTimes(1)
})

test('explains camera permission failure without starting recognition', async () => {
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: vi.fn().mockRejectedValue(new DOMException('denied', 'NotAllowedError')) } })
  const capture = vi.fn()
  render(<WebcamCapture open onClose={vi.fn()} onCapture={capture} />)
  expect(await screen.findByText(/Permita o uso da câmera/)).toBeInTheDocument()
  expect(capture).not.toHaveBeenCalled()
})
