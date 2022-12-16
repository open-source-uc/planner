import { useState } from 'react'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import SemesterColumn from './SemesterColumn'
import CourseCard from './CourseCard'
import type { Course } from '../lib/types'

const CurriculumTable = (props: { courses: Course[] }): JSX.Element => {
  const [courses, setCourses] = useState(props.courses)
  const semseterLists = [...Array(Math.max(...courses.map((course: Course) => course.semestre))).keys()].map((x: number) => x + 1)
  const moveSemester = (course: Course, semester: number): void => {
    const newCourses = [...courses]
    const courseIndex = courses.findIndex((c: Course) => c.ramo.sigla === course.ramo.sigla)
    newCourses[courseIndex].semestre = semester
    console.log(newCourses)
    setCourses(newCourses)
  }

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="CurriculumTable flex flex-row">
        {semseterLists.map((semester: number) => (
            <SemesterColumn key={semester} semester={semester} handleMove={(attr: { course: Course }) => moveSemester(attr.course, semester)}>
              {courses.filter(course => course.semestre === semester).map((course: Course) => (
                <CourseCard key={course.ramo.sigla} course={course}/>
              ))}
            </SemesterColumn>
        ))}
      </div>
    </DndProvider>
  )
}

export default CurriculumTable
