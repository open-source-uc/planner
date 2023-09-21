import { Cyear, type CourseId, type CoursePos, type PseudoCourseId } from './Types'
import { type ValidatablePlan } from '../../../client'

export const getCoursePos = (prevCourses: PseudoCourseId[][], courseId: CourseId): CoursePos | null => {
  const positions: CoursePos[] = []

  prevCourses.forEach((sublist, semester) => {
    sublist.forEach((value, index) => {
      if (value.code === courseId.code) {
        positions.push({ semester, index })
      }
    })
  })
  if (positions.length <= courseId.instance || courseId.instance < 0) {
    return null
  }

  return positions[courseId.instance]
}

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
