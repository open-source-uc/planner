import { type Cyear, type CoursePos, type PseudoCourseId, type Diagnostic } from './Types'
import { type ValidatablePlan, type ClassId, type ValidationResult } from '../../../client'

export const validateCourseMovement = (prev: ValidatablePlan, drag: CoursePos, drop: CoursePos): string | null => {
  const dragCourse = prev.classes[drag.semester][drag.index]

  if (
    dragCourse.is_concrete === true &&
      drop.semester !== drag.semester &&
      drop.semester < prev.classes.length &&
      prev.classes[drop.semester].map(course => course.code).includes(dragCourse.code)
  ) {
    return 'No se puede tener dos cursos iguales en un mismo semestre'
  }

  return null
}

export const updateClassesState = (prev: ValidatablePlan, drag: CoursePos, drop: CoursePos): ValidatablePlan => {
  const newClasses = [...prev.classes]
  const dragSemester = [...newClasses[drag.semester]]

  while (drop.semester >= newClasses.length) {
    newClasses.push([])
  }
  const dropSemester = [...newClasses[drop.semester]]
  const dragCourse = { ...dragSemester[drag.index] }
  const dropIndex = drop.index !== -1 ? drop.index : dropSemester.length
  if (drop.semester === drag.semester) {
    if (dropIndex < drag.index) {
      dragSemester.splice(dropIndex, 0, dragCourse)
      dragSemester.splice(drag.index + 1, 1)
    } else {
      dragSemester.splice(drag.index, 1)
      dragSemester.splice(dropIndex, 0, dragCourse)
    }
  } else {
    dropSemester.splice(dropIndex, 0, dragCourse)
    dragSemester.splice(drag.index, 1)
    newClasses[drop.semester] = dropSemester
  }

  newClasses[drag.semester] = dragSemester

  while (newClasses[newClasses.length - 1].length === 0) {
    newClasses.pop()
  }

  return { ...prev, classes: newClasses }
}

// Ensure that an array stays in sync with a union of string literals
// https://stackoverflow.com/a/70694878/5884836
type ValueOf<T> = T[keyof T]
type NonEmptyArray<T> = [T, ...T[]]
type MustInclude<T, U extends T[]> = [T] extends [ValueOf<U>] ? U : never
function stringUnionToArray<T> () {
  return <U extends NonEmptyArray<T>>(...elements: MustInclude<T, U>) => elements
}
export const VALID_CYEARS = stringUnionToArray<Cyear>()('C2020', 'C2022')

export const validateCyear = (raw: string): Cyear | null => {
  for (const cyear of VALID_CYEARS) {
    if (raw === cyear) {
      return cyear
    }
  }
  return null
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
