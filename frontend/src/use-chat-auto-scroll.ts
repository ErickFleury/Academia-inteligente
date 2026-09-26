import { useLayoutEffect, useRef } from 'react'

export function useChatAutoScroll(messageCount: number, sending: boolean) {
  const chatEndRef = useRef<HTMLDivElement>(null)
  const hasScrolledRef = useRef(false)

  useLayoutEffect(() => {
    chatEndRef.current?.scrollIntoView?.({
      behavior: hasScrolledRef.current ? 'smooth' : 'auto',
      block: 'end',
    })
    hasScrolledRef.current = true
  }, [messageCount, sending])

  return chatEndRef
}
