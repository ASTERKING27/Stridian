import { useCallback, useEffect, useRef, useState } from 'react'
import { useFocusEffect } from 'expo-router'

/* Load something from the API when the screen opens and again whenever one of `deps`
   changes. A failed reload keeps the last good data on screen (the error says why);
   `refresh` is the pull-to-refresh version of `reload`. */
export function useData(fetch, deps = []) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const reload = useCallback(() => fetch().then(d => { setData(d); setError(null); return d }, setError), deps)
  useEffect(() => { reload() }, [reload])
  const refresh = useCallback(async () => { setRefreshing(true); await reload(); setRefreshing(false) }, [reload])
  return { data, setData, error, reload, refreshing, refresh }
}

/* Run `fn` again when the screen comes back into view (a page pushed over it closed) or
   its tab is switched back to — not when it first opens, where useData has just loaded. */
export function useBackInView(fn, active = true) {
  const first = useRef(true)
  const latest = useRef(fn)
  latest.current = fn
  useFocusEffect(useCallback(() => {
    if (first.current) { first.current = false; return }
    if (active) latest.current()
  }, [active]))
}
