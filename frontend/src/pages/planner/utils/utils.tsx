import { type CourseRequirementErr, type ClassId, type ValidationResult } from '../../../client'

import { type PseudoCourseId, type PseudoCourseDetail, type Diagnostic, type CoursePos, isApiError, isCancelError } from './Types'
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

/**
 * Find the semester and index within semester of a class.
 */
export const locateClassInPlan = (plan: PseudoCourseId[][], classId: ClassId): CoursePos | undefined => {
  return getPlanDigest(plan).idToIndex[classId.code]?.[classId.instance]
}

/**
 * Find the class corersponding to a class ID within a plan.
 */
export const findClassInPlan = (plan: PseudoCourseId[][], classId: ClassId): PseudoCourseId | undefined => {
  const coursePos = locateClassInPlan(plan, classId)
  if (coursePos == null) return undefined
  return plan[coursePos.semester][coursePos.index]
}

/**
 * Find the class ID corresponding to a given semester and index.
 */
export const getClassId = (plan: PseudoCourseId[][], coursePos: CoursePos): ClassId => {
  return getPlanDigest(plan).indexToId[coursePos.semester][coursePos.index]
}

/**
 * Check if the plan is outdated based on the validation results.
 */
export const isPlanOutdated = (plan: PseudoCourseId[][], validation: ValidationResult | null): boolean => {
  if (validation == null) return false
  const digest = getValidationDigest(plan, validation)
  return digest.isOutdated
}

/**
 * Get the errors associated with a semester.
 */
export const getSemesterErrors = (plan: PseudoCourseId[][], validation: ValidationResult | null, semesterIdx: number): Diagnostic[] => {
  if (validation == null) return []
  const digest = getValidationDigest(plan, validation)
  return digest.semesters[semesterIdx]?.errors ?? []
}

/**
 * Get the warnings associated with a semester.
 */
export const getSemesterWarnings = (plan: PseudoCourseId[][], validation: ValidationResult | null, semesterIdx: number): Diagnostic[] => {
  if (validation == null) return []
  const digest = getValidationDigest(plan, validation)
  return digest.semesters[semesterIdx]?.warnings ?? []
}

/**
 * Get the superblock that a course is assigned to.
 */
export const getCourseSuperblock = (plan: PseudoCourseId[][], validation: ValidationResult | null, coursePos: CoursePos): string => {
  if (validation == null) return ''
  const digest = getValidationDigest(plan, validation)
  return digest.semesters[coursePos.semester]?.courses?.[coursePos.index]?.superblock ?? ''
}

/**
 * Get the errors associated with a course.
 */
export const getCourseErrors = (plan: PseudoCourseId[][], validation: ValidationResult | null, coursePos: CoursePos): Diagnostic[] => {
  if (validation == null) return []
  const digest = getValidationDigest(plan, validation)
  return digest.semesters[coursePos.semester]?.courses?.[coursePos.index]?.errors ?? []
}

/**
 * Get the warnings associated with a course.
 */
export const getCourseWarnings = (plan: PseudoCourseId[][], validation: ValidationResult | null, coursePos: CoursePos): Diagnostic[] => {
  if (validation == null) return []
  const digest = getValidationDigest(plan, validation)
  return digest.semesters[coursePos.semester]?.courses?.[coursePos.index]?.warnings ?? []
}

interface PlanDigest {
  // Maps `(code, course instance index)` to `(semester, index within semester)`
  idToIndex: Record<string, CoursePos[]>
  // Maps `(semester, index within semester)` to `(code, course instance index)`
  indexToId: ClassId[][]
}

const planDigestCache = new WeakMap<PseudoCourseId[][], PlanDigest>()

const getPlanDigest = (classes: PseudoCourseId[][]): PlanDigest => {
  let digest = planDigestCache.get(classes)
  if (digest == null) {
    digest = {
      idToIndex: {},
      indexToId: []
    }
    for (let i = 0; i < classes.length; i++) {
      const idx2id = []
      for (let j = 0; j < classes[i].length; j++) {
        const c = classes[i][j]
        let reps = digest.idToIndex[c.code]
        if (reps === undefined) {
          reps = []
          digest.idToIndex[c.code] = reps
        }
        idx2id.push({ code: c.code, instance: reps.length })
        reps.push({ semester: i, index: j })
      }
      digest.indexToId.push(idx2id)
    }
    planDigestCache.set(classes, digest)
  }
  return digest
}

export interface CourseValidationDigest {
  // Contains the superblock string
  // The empty string if no superblock is found
  superblock: string
  // Contains the errors associated with this course.
  errors: Diagnostic[]
  // Contains the warnings associated with this course.
  warnings: Diagnostic[]
}
export interface SemesterValidationDigest {
  // Contains the errors associated with this semester.
  errors: Diagnostic[]
  // Contains the warnings associated with this semester.
  warnings: Diagnostic[]
  // The validation digest for each course
  courses: CourseValidationDigest[]
}
export interface ValidationDigest {
  // Information associated to each semester.
  semesters: SemesterValidationDigest[]
  // If `true`, the plan is outdated with respect to the courses that the user has taken.
  // This is computed from the presence of "outdated" diagnostics.
  isOutdated: boolean
}

const validationDigestCache = new WeakMap<ValidationResult, [PseudoCourseId[][], ValidationDigest]>()

const EMPTY_DIGEST: ValidationDigest = {
  semesters: [],
  isOutdated: false
}

export const getValidationDigest = (classes: PseudoCourseId[][] | null, validationResult: ValidationResult | null): ValidationDigest => {
  if (classes == null || validationResult == null) return EMPTY_DIGEST
  let [oldClasses, digest] = validationDigestCache.get(validationResult) ?? [null, null]
  if (classes !== oldClasses) digest = null
  if (digest == null) {
    const planDigest = getPlanDigest(classes)
    digest = {
      semesters: [],
      isOutdated: false
    }
    // Initialize course information
    digest.semesters = classes.map((semester, i) => {
      return {
        errors: [],
        warnings: [],
        courses: semester.map((course, j) => {
          const { code, instance } = planDigest.indexToId[i][j]
          const superblock = validationResult?.course_superblocks?.[code]?.[instance] ?? ''
          return {
            superblock,
            errors: [],
            warnings: []
          }
        })
      }
    })
    // Fill course and semester information with their associated errors
    for (const diag of validationResult.diagnostics) {
      if (diag.kind === 'outdated') {
        digest.isOutdated = true
      }
      if (diag.associated_to != null) {
        for (const assoc of diag.associated_to) {
          if (typeof assoc === 'number') {
            // This error is associated to a semester
            const semDigest = digest.semesters[assoc]
            if (semDigest != null) {
              const diags = diag.is_err ?? true ? semDigest.errors : semDigest.warnings
              diags.push(diag)
            }
          } else {
            // This error is associated to a course
            const coursePos = planDigest.idToIndex[assoc.code]?.[assoc.instance] ?? null
            if (coursePos != null) {
              const courseDigest = digest.semesters[coursePos.semester]?.courses?.[coursePos.index]
              if (courseDigest != null) {
                const diagIndices = diag.is_err ?? true ? courseDigest.errors : courseDigest.warnings
                diagIndices.push(diag)
              }
            }
          }
        }
      }
    }
    validationDigestCache.set(validationResult, [classes, digest])
  }
  return digest
}
