import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import * as SecureStore from 'expo-secure-store'
import { api, setToken, setUnauthorizedHandler } from './api'
import { unregisterPush } from './notifications'

const TOKEN = 'stridian.token'
const ROLE = 'stridian.role'
const SessionContext = createContext(null)

/* Who is signed in on this phone: nobody, a student ({ email, student }) or a coach
   (an admin is a coach with is_admin). The token lives in the phone's secure storage. */
export function SessionProvider({ children }) {
  const [state, setState] = useState({ status: 'loading' })

  const clear = useCallback(() => {
    setToken(null)
    SecureStore.deleteItemAsync(TOKEN).catch(() => {})
    SecureStore.deleteItemAsync(ROLE).catch(() => {})
    setState({ status: 'out' })
  }, [])

  const load = useCallback(async role => {
    try {
      if (role === 'student') setState({ status: 'in', role, me: await api.studentMe() })
      else setState({ status: 'in', role, coach: await api.me() })
    } catch (err) {
      // offline: stay signed in, the screens say so; anything else was handled by the 401 hook
      if (err.offline) setState(s => ({ status: 'in', role, me: s.me, coach: s.coach, error: err.message }))
      else if (err.status !== 401) setState({ status: 'in', role, error: err.message })
    }
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(clear)
    ;(async () => {
      const [t, role] = await Promise.all([SecureStore.getItemAsync(TOKEN), SecureStore.getItemAsync(ROLE)])
        .catch(() => [null, null])
      if (!t) return setState({ status: 'out' })
      setToken(t)
      await load(role || 'coach')
    })()
  }, [clear, load])

  const value = useMemo(() => {
    const keep = (token, role) => {
      setToken(token)
      SecureStore.setItemAsync(TOKEN, token).catch(() => {})
      SecureStore.setItemAsync(ROLE, role).catch(() => {})
    }
    return {
      ...state,
      isAdmin: state.role === 'coach' && !!state.coach?.is_admin,
      signedInStudent: res => { keep(res.token, 'student'); setState({ status: 'in', role: 'student', me: res.me }) },
      signedInCoach: res => { keep(res.token, 'coach'); setState({ status: 'in', role: 'coach', coach: res.coach }) },
      setMe: me => setState(s => ({ ...s, me, error: undefined })),
      setCoach: coach => setState(s => ({ ...s, coach, error: undefined })),
      refresh: () => load(state.role),
      forget: clear,                 // the account is gone: just drop the token
      signOut: async () => {
        await unregisterPush()
        await (state.role === 'student' ? api.studentLogout() : api.logout()).catch(() => {})
        clear()
      },
    }
  }, [state, clear, load])

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export const useSession = () => useContext(SessionContext)

// "FOOTBALL · MEN", "FOOTBALL · COACH", "ADMIN · FOOTBALL" — the top right of every tab
export function contextLine(s) {
  if (s.role === 'student') {
    const st = s.me?.student
    if (!st) return ''
    return st.sport.toUpperCase() + (st.category ? ` · ${st.category === 'W' ? 'WOMEN' : 'MEN'}` : '')
  }
  const sport = (s.coach?.sport ?? '').toUpperCase()
  return s.isAdmin ? `ADMIN · ${sport}` : `${sport} · COACH`
}
