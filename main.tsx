import React from 'react'
import ReactDOM from 'react-dom/client'
import TestnetFirstApp from './TestnetFirstApp'
import AppErrorBoundary from './AppErrorBoundary'
import WebAccessGate from './WebAccessGate'
import { installAuthorizedFetch } from './api'
import './terminal-theme.css'

installAuthorizedFetch()
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><AppErrorBoundary><WebAccessGate><TestnetFirstApp/></WebAccessGate></AppErrorBoundary></React.StrictMode>)
