import { useState, useEffect } from 'react'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import SemesterColumn from './SemesterColumn'
import CourseCard from './CourseCard'
import type { Course } from '../lib/types'

const CurriculumTable = (props: { coursesProp: any, remCourse:Function, addCourse: Function }): JSX.Element => {
  const [courses, setCourses] = useState(props.coursesProp)
  // por alguna razon se buggea cuando inicia en estado false, asi que se inicia en true y se cambia a false cuando se termina de renderizar. Que asco
  const [isDragging, setIsDragging] = useState(true)
  useEffect(() => {
    setIsDragging(false)
  }, [props.coursesProp])
  const semseterLists = [...Array(Math.max(...courses.map((course: Course) => course.semestre))).keys()].map((x: number) => x + 1)
  const moveCard = (target: Course, drag: any): void => {
    setCourses(prev => {
      const courseIndex = prev.findIndex((c: Course) => c.ramo.sigla === drag.course.ramo.sigla)
      const targetIndex = prev.findIndex((c: Course) => c.ramo.sigla === target.ramo.sigla)
      const newCourses = [...prev]
      newCourses.splice(targetIndex, 0, newCourses[courseIndex])
      newCourses[targetIndex].semestre = target.semestre
      if (courseIndex > targetIndex) {
        newCourses.splice(courseIndex + 1, 1)
      } else {
        newCourses.splice(courseIndex, 1)
      }
      return newCourses
    })
  }
  const addEnd = (semester: number, drag: any): void => {
    setCourses(prev => {
      const courseIndex = prev.findIndex((c: Course) => c.ramo.sigla === drag.course.ramo.sigla)
      const newCourses = [...prev]
      // get index of last course in a semester before semester
      const lastCourseIndex = newCourses.reduce((acc: number, curr: Course, index: number) => {
        if (curr.semestre <= semester) {
          return index
        }
        return acc
      }, 0)
      newCourses.splice(lastCourseIndex + 1, 0, newCourses[courseIndex])
      newCourses[lastCourseIndex + 1].semestre = semester
      if (courseIndex > lastCourseIndex) {
        newCourses.splice(courseIndex + 1, 1)
      } else {
        newCourses.splice(courseIndex, 1)
      }
      return newCourses
    })
  }
  return (
    <DndProvider backend={HTML5Backend}>
      <div className="CurriculumTable flex flex-row">
        {semseterLists.map((semester: number) => (
            <SemesterColumn key={semester} semester={semester} addEnd={(drag: any) => addEnd(semester, drag)}>
              {courses.filter(course => course.semestre === semester).map((course: Course) => (
                <CourseCard key={course.ramo.sigla} course={course} isDragging={(e: boolean) => setIsDragging(e)} handleMove={(drag: any) => moveCard(course, drag)}/>
              ))}
            </SemesterColumn>
        ))}
        {isDragging && <>
          <SemesterColumn key={semseterLists.length + 1} semester={semseterLists.length + 1} addEnd={(drag: any) => addEnd(semseterLists.length + 1, drag)} />
          <SemesterColumn key={semseterLists.length + 2} semester={semseterLists.length + 2} addEnd={(drag: any) => addEnd(semseterLists.length + 2, drag)} />
        </>}
      </div>
    </DndProvider>
  )
}

export default CurriculumTable
