import { type CourseRequirementErr, type Cyear, type ClassId } from '../../../client'

import { type PseudoCourseDetail } from './Types'
type RequirementExpr = CourseRequirementErr['missing']

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

export const validateCyear = (raw: string): Cyear | null => {
    // Ensure that an array stays in sync with a union of string literals
    // https://stackoverflow.com/a/70694878/5884836
    type ValueOf<T> = T[keyof T]
    type NonEmptyArray<T> = [T, ...T[]]
    type MustInclude<T, U extends T[]> = [T] extends [ValueOf<U>] ? U : never
    function stringUnionToArray<T> () {
      return <U extends NonEmptyArray<T>>(...elements: MustInclude<T, U>) => elements
    }

    const validCyears = stringUnionToArray<Cyear['raw']>()('C2020')
    for (const cyear of validCyears) {
      if (raw === cyear) {
        return { raw: cyear }
      }
    }
    return null
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
