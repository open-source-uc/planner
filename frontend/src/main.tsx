import { RouterProvider } from '@tanstack/react-router'
import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'

import { AuthProvider, AuthState } from './contexts/auth.context'

import router from './router'

function App (): JSX.Element {
  const user = localStorage.getItem('user')
  const userData = (user != null) ? JSON.parse(user) as AuthState : null

  return (
    <AuthProvider userData={userData}>
      <RouterProvider router={router}/>
    </AuthProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
