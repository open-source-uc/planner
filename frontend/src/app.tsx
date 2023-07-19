import { AuthProvider, useToken } from './contexts/auth.context'
import { RouterProvider } from '@tanstack/react-router'

import router from './router'
import { ConfettiProvider } from './contexts/confetti.context'

export default function App (): JSX.Element {
  return (
    <ConfettiProvider>
      <AuthProvider userData={useToken()}>
        <RouterProvider router={router}/>
      </AuthProvider>
    </ConfettiProvider>
  )
}
