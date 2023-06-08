import { RouterProvider } from '@tanstack/react-router'
import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'

import { AuthProvider, useToken } from './contexts/auth.context'

import { OpenAPI } from './client'

import router from './router'

import { toastConfig } from './utils/toastConfig'

toastConfig()

function App (): JSX.Element {
  return (
    <AuthProvider userData={useToken()}>
      <RouterProvider router={router}/>
    </AuthProvider>
  )
}
const baseUrl = import.meta.env.VITE_BASE_API_URL
if (typeof baseUrl !== 'string') {
  throw new Error('VITE_BASE_API_URL environment variable not set during build')
}
OpenAPI.BASE = baseUrl
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
