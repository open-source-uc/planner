
import { type ClassId, type CourseRequirementErr, type ApiError, type Major, type Minor, type Title, type CourseDetails, type EquivDetails, type ConcreteId, type EquivalenceId, type CurriculumSpec, type ValidationResult } from '../../../client'

export interface CoursePos { semester: number, index: number }
export type PseudoCourseId = ConcreteId | EquivalenceId
export type PseudoCourseDetail = CourseDetails | EquivDetails
export type ModalData = { equivalence: EquivDetails | undefined, selector: boolean, semester: number, index?: number } | undefined
export type Cyear = CurriculumSpec['cyear']
export type Diagnostic = ValidationResult['diagnostics'][number]
export type RequirementExpr = CourseRequirementErr['missing']

export interface CurriculumData {
  majors: Record<string, Major>
  minors: Record<string, Minor>
  titles: Record<string, Title>
  ofCyear: string
  ofMajor?: string
}
export const isApiError = (err: any): err is ApiError => {
  return err.status !== undefined
}
export const isCancelError = (err: any): boolean => {
  return err.name !== undefined && err.name === 'CancelError'
}

export const isCourseRequirementErr = (diag: any): diag is CourseRequirementErr => {
  return diag.kind === 'req'
}

export type PossibleBlocksList = Record<string, EquivDetails[]>

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

export interface PlanDigest {
  // Maps `(code, course instance index)` to `(semester, index within semester)`
  idToIndex: Record<string, CoursePos[]>
  // Maps `(semester, index within semester)` to `(code, course instance index)`
  indexToId: ClassId[][]
}
