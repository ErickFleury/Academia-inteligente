import { createContext } from 'react'

import type { Session } from './auth'

// Uses the same backend-verified session that controls application routing.
export const SessionContext = createContext<Session | null>(null)
