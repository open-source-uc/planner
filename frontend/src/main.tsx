import { RouterProvider } from '@tanstack/react-router'
import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'

import { AuthProvider, useToken } from './contexts/auth.context'

import router from './router'

function App (): JSX.Element {
  return (
    <AuthProvider userData={useToken()}>
      <RouterProvider router={router}/>
    </AuthProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
