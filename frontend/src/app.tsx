import { AuthProvider, useToken } from './contexts/auth.context'
import { RouterProvider } from '@tanstack/react-router'

import router from './router'

export default function App (): JSX.Element {
  return (
      <AuthProvider userData={useToken()}>
        <RouterProvider router={router}/>
      </AuthProvider>
  )
}
