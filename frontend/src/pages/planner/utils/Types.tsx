
import { type ApiError, type Major, type Minor, type Title, type CourseDetails, type EquivDetails, type ConcreteId, type EquivalenceId } from '../../../client'

export interface CoursePos { semester: number, index: number }
export interface CourseId { code: string, instance: number }
export type PseudoCourseId = ConcreteId | EquivalenceId
export type PseudoCourseDetail = CourseDetails | EquivDetails
export type ModalData = { equivalence: EquivDetails | undefined, selector: boolean, semester: number, index?: number } | undefined

export interface CurriculumData {
  majors: Record<string, Major>
  minors: Record<string, Minor>
  titles: Record<string, Title>
}
export interface PlanDigest {
  // Maps `(code, course instance index)` to `(semester, index within semester)`
  idToIndex: Record<string, Array<[number, number]>>
  // Maps `(semester, index within semester)` to `(code, course instance index)`
  indexToId: Array<Array<{ code: string, instance: number }>>
}
export interface CourseValidationDigest {
  // Contains the superblock string
  // The empty string if no superblock is found
  superblock: string
  // Contains the indices of any errors associated with this course
  errorIndices: number[]
  // Contains the indices of any warnings associated with this course
  warningIndices: number[]
}
export interface SemesterValidationDigest {
  // Contains the indices of any errors associated with this semester.
  errorIndices: number[]
  // Contains the indices of any warnings associated with this semester.
  warningIndices: number[]
}
export interface ValidationDigest {
  // Information associated to each semester.
  semesters: SemesterValidationDigest[]
  // Information associated to each course.
  courses: CourseValidationDigest[][]
  // If `true`, the plan is outdated with respect to the courses that the user has taken.
  // This is computed from the presence of "outdated" diagnostics.
  isOutdated: boolean
}
export const isApiError = (err: any): err is ApiError => {
  return err.status !== undefined
}
export const isCancelError = (err: any): boolean => {
  return err.name !== undefined && err.name === 'CancelError'
}
