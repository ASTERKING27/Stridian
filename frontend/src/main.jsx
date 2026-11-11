import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Analytics } from '@vercel/analytics/react'
import '@fontsource-variable/archivo/wdth.css'
import '@fontsource/ibm-plex-mono/latin-400.css'
import '@fontsource/ibm-plex-mono/latin-500.css'
import App from './App.jsx'
import './styles.css'
import './system.css'
// the public site's own styles come last, so they win over the app's where names meet
import './site/court.css'
import './site/home.css'
import './site/signin.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
    {/* Vercel Web Analytics: anonymous page views, no cookies */}
    {__ON_VERCEL__ && <Analytics />}
  </StrictMode>
)
