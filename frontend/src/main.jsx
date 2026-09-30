import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Analytics } from '@vercel/analytics/react'
import '@fontsource-variable/inter'
import '@fontsource-variable/space-grotesk'
import App from './App.jsx'
import './styles.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
    {/* Vercel Web Analytics: anonymous page views, no cookies */}
    {__ON_VERCEL__ && <Analytics />}
  </StrictMode>
)
