import { type CourseRequirementErr, type ClassId } from '../../../client'

import { type PseudoCourseDetail, isApiError, isCancelError } from './Types'
import { toast } from 'react-toastify'

type RequirementExpr = CourseRequirementErr['missing']

export enum PlannerStatus {
  LOADING = 'LOADING',
  CHANGING_CURRICULUM = 'CHANGING_CURRICULUM',
  VALIDATING = 'VALIDATING',
  SAVING = 'SAVING',
  ERROR = 'ERROR',
  READY = 'READY',
}

export const collectRequirements = (expr: RequirementExpr, into: Set<string>): void => {
  switch (expr.expr) {
    case 'and': case 'or':
      for (const child of expr.children) {
        collectRequirements(child, into)
      }
      break
    case 'req':
      into.add(expr.code)
      break
  }
}

/**
 * Show the name of a course with the code if it is loaded, if not show the code only.
 */
export const getCourseNameWithCode = (course: ClassId | PseudoCourseDetail): string => {
  if ('name' in course) {
    return `"${course.name}" [${course.code}]`
  } else {
    // If the course details are not available, fallback to just the code
    return course.code
  }
}

/**
 * Show the name of a course if it is loaded.
 */
export const getCourseName = (course: ClassId | PseudoCourseDetail): string | undefined => {
  //   if str, return unchanged
  if (typeof course === 'string') {
    return course
  }
  if ('name' in course) {
    return course.name
  } else {
    return undefined
  }
}

export const handleErrors = (err: unknown, setPlannerStatus: Function, setError: Function, isMod?: boolean): void => {
  if (isApiError(err)) {
    console.error(err)
    switch (err.status) {
      case 401:
        console.log('token invalid or expired, loading re-login page')
        toast.error('Tu session a expirado. Redireccionando a pagina de inicio de sesion...', {
          toastId: 'ERROR401'
        })
        break
      case 403:
        toast.warn('No tienes permisos para realizar esa accion')
        break
      case 404:
        setError('El planner al que estas intentando acceder no existe o no es de tu propiedad')
        break
      case 429:
        toast.error('Se alcanzó el límite de actividad, espera y vuelve a intentarlo')
        return
      case 500:
        setError(err.message)
        break
      default:
        console.log(err.status)
        setError('Error desconocido')
        break
    }
    setPlannerStatus(PlannerStatus.ERROR)
  } else if (!isCancelError(err)) {
    setError('Error desconocido')
    console.error(err)
    setPlannerStatus(PlannerStatus.ERROR)
  }
}
