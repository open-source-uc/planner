import React, { Dispatch, SetStateAction } from 'react'

export interface UserData {
  token: string
}

export interface AuthState {
  user: UserData | null
  setUser: Dispatch<SetStateAction<UserData | null>> | null
}

interface Props {
  children: React.ReactNode
  userData: UserData | null
}

const AuthContext = React.createContext<AuthState | null>(null)

export function AuthProvider ({ children, userData }: Props): JSX.Element {
  const [user, setUser] = React.useState<UserData | null>(userData)

  return (
    <AuthContext.Provider value={{ user, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}
export function useToken (): UserData | null {
  // Check if we have a new token in the search params
  const urlParams = new URLSearchParams(window.location.search)
  let token = urlParams.get('token')
  if (token != null) {
    // Save token to local storage
    localStorage.setItem('access-token', token)
    // Remove token from search params
    window.history.replaceState({}, document.title, '/')
  }
  // Check if we have a token in local storage
  token = localStorage.getItem('access-token')
  if (token != null) {
    return {
      token
    }
  }
  return null
}

export const useAuth = (): AuthState | null => React.useContext(AuthContext)
