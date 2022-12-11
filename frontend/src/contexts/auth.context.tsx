import React, { Dispatch, SetStateAction } from 'react'

interface UserData {
  token: string
}

export interface AuthState {
  user: UserData | null
  setUser: Dispatch<SetStateAction<AuthState | null>>
}

interface Props {
  children: React.ReactNode
  userData: AuthState | null
}

const AuthContext = React.createContext<AuthState | null>(null)

export function AuthProvider ({ children, userData }: Props): JSX.Element {
  const [user, setUser] = React.useState(userData)

  return (
    <AuthContext.Provider value={{ user, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthState | null => React.useContext(AuthContext)
