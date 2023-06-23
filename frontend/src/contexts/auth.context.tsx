import React, { Dispatch, SetStateAction, useEffect, useState } from 'react'
import { DefaultService, StudentInfo, ConcreteId, EquivalenceId } from '../client'

export interface UserData {
  token: string
}

export interface AuthState {
  user: UserData | null
  setUser: Dispatch<SetStateAction<UserData | null>> | null
  info: StudentInfo | null
  passed: Array<Array<(ConcreteId | EquivalenceId)>> | null
}

interface Props {
  children: React.ReactNode
  userData: UserData | null
}

const AuthContext = React.createContext<AuthState | null>(null)

export function AuthProvider ({ children, userData }: Props): JSX.Element {
  const [user, setUser] = React.useState<UserData | null>(userData)
  const [info, setInfo] = useState <StudentInfo | null>(null)
  const [passed, setPassed] = useState <Array<Array<(ConcreteId | EquivalenceId)>>>([])

  const getInfo = async (): Promise<void> => {
    if (user != null) {
      const response = await DefaultService.getStudentInfo()
      setInfo(response.info)
      setPassed(response.passed_courses)
    } else {
      setInfo(null)
      setPassed([])
    }
  }

  useEffect(() => {
    getInfo().catch(err => {
      console.log(err)
      if (err.status === 401) {
        console.log('token invalid or expired, loading re-login page')
      }
    })
  }, [user])

  return (
    <AuthContext.Provider value={{ user, setUser, info, passed }}>
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
