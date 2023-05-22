import { RouterProvider } from '@tanstack/react-router'
import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'

import { AuthProvider, useToken } from './contexts/auth.context'

import { OpenAPI } from './client'

import router from './router'

function App (): JSX.Element {
  return (
    <AuthProvider userData={useToken()}>
      <RouterProvider router={router}/>
    </AuthProvider>
  )
}
OpenAPI.BASE = import.meta.env.VITE_BASE_API_URL // TODO: Make this work for production
// OpenAPI.BASE = 'http://localhost:8000'
OpenAPI.TOKEN = async () => {
  const token = localStorage.getItem('access-token')
  if (token != null) {
    return token
  }
  return ''
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
