/* eslint-disable react/prop-types */
import { useAuth } from '../contexts/auth.context'
import router from '../router'

interface ProtectProps {
  children: JSX.Element
}

function Protect ({ children }: ProtectProps): JSX.Element {
  const authState = useAuth()

  if (authState == null || authState.user == null) {
    void router.navigate('/login')
  }

  return children
}

export default Protect
