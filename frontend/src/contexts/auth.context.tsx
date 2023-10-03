import React, { type Dispatch, type SetStateAction, useEffect, useState } from 'react'
import { DefaultService, type StudentContext } from '../client'
import { toast } from 'react-toastify'

export interface UserData {
  token: string
}

interface Student extends StudentContext {
  rut?: string
}

export interface AuthState {
  user: UserData | null
  isMod: boolean | null
  isAdmin: boolean | null
  setUser: Dispatch<SetStateAction<UserData | null>> | null
  student: Student | null
  setStudent: Dispatch<SetStateAction<Student | null>> | null
}

interface Props {
  children: React.ReactNode
  userData: UserData | null
}

const AuthContext = React.createContext<AuthState | null>(null)

export function AuthProvider ({ children, userData }: Props): JSX.Element {
  const [user, setUser] = React.useState<UserData | null>(userData)
  const [isMod, setIsMod] = React.useState<boolean >(false)
  const [isAdmin, setIsAdmin] = React.useState<boolean >(false)
  const [student, setStudent] = useState<Student | null>(null)

  useEffect(() => {
    if (user?.token == null) {
      console.log('not fetching student info: no token')
      return
    }
    void DefaultService.getStudentInfo().catch(err => {
      if (err.status === 401) {
        console.log('Token invalid or expired, loading re-login page...')
        toast.error('Tu sesión ha expirado. Redireccionando a página de inicio de sesión..', {
          toastId: 'ERROR401'
        })
      } else if (err.status === 403) {
        console.log('El usuario no es un estudiante de ingeniería vigente, cerrando sesión...')
        toast.error('No eres un estudiante de ingeniería vigente. Cerrando la sesión..', {
          toastId: 'ERROR403'
        })
      } else {
        toast.error('Error al cargar información del usuario', {
          toastId: 'ERROR401'
        })
      }
    }).then(
      student => {
        if (student != null) {
          setStudent((_prevStudent) => student)
        }
      })
    void DefaultService.checkMod().catch(err => {
      if (err.status === 401) {
        console.log('Token invalid or expired, loading re-login page...')
        toast.error('Tu sesión ha expirado. Redireccionando a página de inicio de sesión..', {
          toastId: 'ERROR401'
        })
      } else if (err.status === 403) {
        console.log('El usuario no tiene permisos de mod')
        setIsMod(() => false)
      } else {
        toast.error('Error al cargar información del usuario', {
          toastId: 'ERROR401'
        })
      }
    }).then(
      response => {
        if (response !== undefined && response.stat !== 200) {
          setIsMod(true)
        }
      })
    void DefaultService.checkAdmin().catch(err => {
      if (err.status === 401) {
        console.log('Token invalid or expired, loading re-login page...')
        toast.error('Tu sesión ha expirado. Redireccionando a página de inicio de sesión..', {
          toastId: 'ERROR401'
        })
      } else if (err.status === 403) {
        console.log('El usuario no tiene permisos de admin')
        setIsAdmin(() => false)
      } else {
        toast.error('Error al cargar información del usuario', {
          toastId: 'ERROR401'
        })
      }
    }).then(
      response => {
        if (response !== undefined && response.stat !== 200) {
          setIsAdmin(true)
        }
      })
  }, [user?.token])

  return (
    <AuthContext.Provider value={{ user, setUser, student, setStudent, isMod, isAdmin }}>
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
