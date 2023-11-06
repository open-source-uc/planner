
import { type CourseRequirementErr, type UnknownCourseErr, type SemestralityWarn, type UnavailableCourseWarn, type AmbiguousCourseErr, type ApiError, type Major, type Minor, type Title, type CourseDetails, type EquivDetails, type ConcreteId, type EquivalenceId, type CurriculumSpec, type ValidationResult } from '../../../client'

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

export const isDiagWithAssociatedCourses = (diag: any): diag is (CourseRequirementErr | UnknownCourseErr | SemestralityWarn | UnavailableCourseWarn | AmbiguousCourseErr) => {
  return 'associated_to' in diag && diag.associated_to !== null && diag.associated_to !== undefined && typeof diag.associated_to[0] === 'object'
}

export const isCourseRequirementErr = (diag: any): diag is CourseRequirementErr => {
  return diag.kind === 'req'
}
