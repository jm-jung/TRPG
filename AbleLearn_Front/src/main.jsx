import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import Panel from './component/MainPanel/Panel.jsx'
import './index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Panel></Panel>
  </StrictMode>
)
