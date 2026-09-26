import { render } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { useChatAutoScroll } from './use-chat-auto-scroll'

const originalScrollIntoView = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollIntoView')

function ChatEnd({ messageCount, sending }: { messageCount: number; sending: boolean }) {
  const ref = useChatAutoScroll(messageCount, sending)
  return <div ref={ref} />
}

afterEach(() => {
  if (originalScrollIntoView) Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', originalScrollIntoView)
  else delete (HTMLElement.prototype as Partial<HTMLElement>).scrollIntoView
})

test('opens at the chat end and follows sent messages', () => {
  const scrollIntoView = vi.fn()
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { configurable: true, value: scrollIntoView })

  const { rerender } = render(<ChatEnd messageCount={3} sending={false} />)
  expect(scrollIntoView).toHaveBeenLastCalledWith({ behavior: 'auto', block: 'end' })

  rerender(<ChatEnd messageCount={4} sending={false} />)
  expect(scrollIntoView).toHaveBeenLastCalledWith({ behavior: 'smooth', block: 'end' })
})
