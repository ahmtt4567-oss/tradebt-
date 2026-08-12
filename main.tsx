import React from 'react'
import ReactDOM from 'react-dom/client'
import TestnetFirstApp from './TestnetFirstApp'
import AppErrorBoundary from './AppErrorBoundary'
import WebAccessGate from './WebAccessGate'
import { installAuthorizedFetch } from './api'
import './style.css'
import './binance-demo.css'
import './execution-v25.css'
import './web-access.css'
import './testnet-first.css'
import './cloud-ops-v27.css'

installAuthorizedFetch()
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><AppErrorBoundary><WebAccessGate><TestnetFirstApp/></WebAccessGate></AppErrorBoundary></React.StrictMode>)
