import { useState } from 'react'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import SemesterColumn from './SemesterColumn'
import CourseCard from './CourseCard'
import type { Course } from '../lib/types'

const CurriculumTable = (props: { coursesProp: Course[] }): JSX.Element => {
  const [courses, setCourses] = useState(props.coursesProp)
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
      console.log(newCourses)
      return newCourses
    })
  }

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="CurriculumTable flex flex-row">
        {semseterLists.map((semester: number) => (
            <SemesterColumn key={semester} semester={semester}>
              {courses.filter(course => course.semestre === semester).map((course: Course) => (
                <CourseCard key={course.ramo.sigla} course={course} handleMove={(drag: any) => moveCard(course, drag)}/>
              ))}
              <></>
            </SemesterColumn>
        ))}
      </div>
    </DndProvider>
  )
}

export default CurriculumTable
