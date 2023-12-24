import { type CourseRequirementErr, type ClassId, type ValidatablePlan, type CancelablePromise, type ValidationResult, type ConcreteId, type EquivalenceId, type CourseDetails } from '../../../client'

import { DefaultService } from '../../../client'
import { type PseudoCourseDetail, type Cyear, type PseudoCourseId, isApiError, isCancelError, isCourseRequirementErr, type ModalData } from './Types'
import { toast } from 'react-toastify'
import { type AuthState } from '../../../contexts/auth.context'
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
export const getCourseName = (course: string | ClassId | PseudoCourseDetail): string | undefined => {
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

/**
 * Get the correspond validation promise for the current user and mode.
 */
export const getValidationPromise = (validatablePlan: ValidatablePlan, authState: AuthState | null, impersonateRut?: string): CancelablePromise<ValidationResult> => {
  if (authState?.user == null) {
    return DefaultService.validateGuestPlan(validatablePlan)
  } else if (authState?.isMod === true && impersonateRut != null) {
    return DefaultService.validatePlanForAnyUser(impersonateRut, validatablePlan)
  } else {
    return DefaultService.validatePlanForUser(validatablePlan)
  }
}

/**
 * Empty validationPromise if it have one and update ref to be empty.
 */
export const handleEmptyPlan = (validatablePlan: ValidatablePlan, setValidationPromise: React.Dispatch<React.SetStateAction<CancelablePromise<any> | null>>, previousClasses: { current: Array<Array<ConcreteId | EquivalenceId>> }, previousCurriculum: { current: { major: string | undefined, minor: string | undefined, title: string | undefined, cyear?: Cyear } }): void => {
  setValidationPromise(prev => {
    if (prev != null) {
      prev.cancel()
      return null
    }
    return prev
  })
  updateClassesRef(validatablePlan, previousClasses, previousCurriculum)
}

/**
 * Update ref to be the same as the current classes.
 */
export const updateClassesRef = (validatablePlan: ValidatablePlan, previousClasses: { current: PseudoCourseId[][] }, previousCurriculum: { current: { major: string | undefined, minor: string | undefined, title: string | undefined, cyear?: Cyear } }): void => {
  if (previousClasses.current !== validatablePlan.classes) {
    previousClasses.current = validatablePlan.classes
  }
  previousCurriculum.current = {
    major: validatablePlan.curriculum.major,
    minor: validatablePlan.curriculum.minor,
    title: validatablePlan.curriculum.title,
    cyear: validatablePlan.curriculum.cyear
  }
}

/**
 * Collect all the required courses from the diagnostics.
 */
export const collectRequiredCourses = (diagnostics: any[]): PseudoCourseId[] => {
  const reqCourses = new Set<string>()
  for (const diag of diagnostics) {
    if (isCourseRequirementErr(diag)) {
      collectRequirements(diag.modernized_missing, reqCourses)
    }
  }
  return Array.from(reqCourses).map((code: string) => { return { code, isConcrete: true } })
}

/**
 * Order the diagnostics by error first.
 */
export const orderValidationDiagnostics = (response: ValidationResult): void => {
  response.diagnostics.sort((a, b) => {
    if (a.is_err === b.is_err) {
      return 0
    } else if (a.is_err ?? true) {
      return -1
    } else {
      return 1
    }
  })
}

/*
  * Handle the selection of a course in the modal. This function will return a new validatable plan with the selected course and would handle the creddits of the equivalence if it is needed.
*/
export const handleSelectEquivalence = (selection: CourseDetails, prev: ValidatablePlan, modalData: ModalData): ValidatablePlan | null => {
  if (modalData === undefined) return prev
  const { equivalence, semester } = modalData
  const newValidatablePlan = { ...prev, classes: [...prev.classes] }
  while (newValidatablePlan.classes.length <= semester) {
    newValidatablePlan.classes.push([])
  }
  const index = modalData?.index ?? newValidatablePlan.classes[semester].length
  const pastClass = newValidatablePlan.classes[semester][index]
  if (pastClass !== undefined && selection.code === pastClass.code) { return prev }
  for (const existingCourse of newValidatablePlan.classes[semester].flat()) {
    if (existingCourse.code === selection.code) {
      toast.error(`${selection.name} ya se encuentra en este semestre, seleccione otro curso por favor`)
      return prev
    }
  }
  newValidatablePlan.classes[semester] = [...newValidatablePlan.classes[semester]]
  if (equivalence === undefined) {
    while (newValidatablePlan.classes.length <= semester) {
      newValidatablePlan.classes.push([])
    }
    newValidatablePlan.classes[semester][index] = {
      is_concrete: true,
      code: selection.code,
      equivalence: undefined
    }
  } else {
    const oldEquivalence = 'credits' in pastClass ? pastClass : pastClass.equivalence

    newValidatablePlan.classes[semester][index] = {
      is_concrete: true,
      code: selection.code,
      equivalence: oldEquivalence
    }
    if (oldEquivalence !== undefined && oldEquivalence.credits !== selection.credits) {
      if (oldEquivalence.credits > selection.credits) {
        newValidatablePlan.classes[semester].splice(index, 1,
          {
            is_concrete: true,
            code: selection.code,
            equivalence: {
              ...oldEquivalence,
              credits: selection.credits
            }
          },
          {
            is_concrete: false,
            code: oldEquivalence.code,
            credits: oldEquivalence.credits - selection.credits
          }
        )
      } else {
        // handle when credis exced necesary
        // Partial solution: just consume anything we find
        const semesterClasses = newValidatablePlan.classes[semester]
        let extra = selection.credits - oldEquivalence.credits
        for (let i = semesterClasses.length; i-- > 0;) {
          const equiv = semesterClasses[i]
          if ('credits' in equiv && equiv.code === oldEquivalence.code) {
            if (equiv.credits <= extra) {
              // Consume this equivalence entirely
              semesterClasses.splice(index, 1)
              extra -= equiv.credits
            } else {
              // Consume part of this equivalence
              equiv.credits -= extra
              extra = 0
            }
          }
        }

        // Increase the credits of the equivalence
        // We might not have found all the missing credits, but that's ok
        newValidatablePlan.classes[semester].splice(index, 1,
          {
            is_concrete: true,
            code: selection.code,
            equivalence: {
              ...oldEquivalence,
              credits: selection.credits
            }
          }
        )
      }
    }
  }
  return newValidatablePlan
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
