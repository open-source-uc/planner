import { useState } from 'react'
import SemesterColumn from './SemesterColumn'
import CourseCard from './CourseCard'
import { Course, FlatValidationResult } from '../../../client'
import { PseudoCourseId, PseudoCourseDetail } from '../Planner'
import 'react-toastify/dist/ReactToastify.css'
import { toast } from 'react-toastify'

interface PlanBoardProps {
  classesGrid: PseudoCourseId[][] | null
  classesDetails: { [code: string]: PseudoCourseDetail }
  setClassesGrid: Function
  openModal: Function
  addCourse: Function
  validating: Boolean
  validationResult: FlatValidationResult | null
}

const findCourseSuperblock = (validationResults: FlatValidationResult | null, semester: number, index: number): string | null => {
  if (validationResults == null) return null
  if (semester >= validationResults.course_superblocks.length || index >= validationResults.course_superblocks[semester].length) return null
  const rawSuperblock = validationResults.course_superblocks[semester][index]
  return rawSuperblock.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(' ', '').split(' ')[0]
}

/**
 * The main drag-n-drop planner interface.
 * Displays several semesters, as well as several classes per semester.
 */

const PlanBoard = ({ classesGrid, classesDetails, setClassesGrid, openModal, addCourse, validating, validationResult }: PlanBoardProps): JSX.Element => {
  const [isDragging, setIsDragging] = useState(false)

  function remCourse (semIdx: number, code: string): void {
    if (classesGrid === null) return
    let idx = -1
    for (let i = 0; i < classesGrid[semIdx].length; i++) {
      if (classesGrid[semIdx][i].code === code) {
        idx = i
        break
      }
    }
    if (idx === -1) return
    const newClassesGrid = classesGrid
    newClassesGrid[semIdx].splice(idx, 1)
    while (newClassesGrid[newClassesGrid.length - 1].length === 0) {
      newClassesGrid.pop()
    }
    setClassesGrid(newClassesGrid)
  }

  function moveCourse (semester: number, drag: { name: string, code: string, index: number, semester: number, credits?: number, is_concrete?: boolean }, index: number): void {
    if (classesGrid === null) {
      return
    }
    if (drag.is_concrete === true && semester < classesGrid.length && classesGrid[semester].map(course => course.code).includes(drag.code)) {
      toast.error('No se puede tener dos ramos iguales en un mismo semestre')
    } else {
      const newClassesGrid = classesGrid
      if (semester - classesGrid.length >= 0) {
        if (semester - classesGrid.length > 0) newClassesGrid.push([])
        newClassesGrid.push([])
      }
      newClassesGrid[semester].splice(index, 0, newClassesGrid[drag.semester][drag.index])
      if (semester === drag.semester && index < drag.index) {
        newClassesGrid[drag.semester].splice(drag.index + 1, 1)
      } else {
        newClassesGrid[drag.semester].splice(drag.index, 1)
      }
      while (newClassesGrid[newClassesGrid.length - 1].length === 0) {
        newClassesGrid.pop()
      }
      setClassesGrid(newClassesGrid)
    }
  }
  return (
      <div className= {`CurriculumTable overflow-x-auto flex flex-row flex-nowrap rtl-grid flex-grow ${validating === true ? 'pointer-events-none' : ''}`}>
        {classesGrid === null
          ? <h1>elija plan</h1>
          : <>
            {classesGrid.map((classes: PseudoCourseId[], semester: number) => (
                <SemesterColumn
                  key={semester}
                  semester={semester + 1}
                  addEnd={(dragCourse: Course & { index: number, semester: number }) => moveCourse(semester, dragCourse, classes.length)}
                >
                  {classes?.map((course: PseudoCourseId, index: number) => (
                    <CourseCard
                      key={index.toString() + course.code}
                      cardData={{ ...course, semester, index, ...classesDetails[course.code] }}
                      isDragging={(e: boolean) => setIsDragging(e)}
                      handleMove={(dragCourse: Course & { index: number, semester: number }) => moveCourse(semester, dragCourse, index)}
                      remCourse={() => remCourse(semester, course.code)}
                      courseBlock={findCourseSuperblock(validationResult, semester, index)}
                      openSelector={() => { if ('credits' in course) openModal(course, semester, index); else openModal(course.equivalence, semester, index) }}
                      hasEquivalence={course.is_concrete === false || ('equivalence' in course && course.equivalence != null)}
                      hasError={validationResult?.diagnostics?.find((e) => e.course_index?.semester === semester && e.course_index?.position === index && !e.is_warning) != null}
                      hasWarning={validationResult?.diagnostics?.find((e) => e.course_index?.semester === semester && e.course_index?.position === index && e.is_warning) != null}
                    />
                  ))}
                  {!isDragging && <div className="h-10 mx-2 bg-slate-300 card">
                  <button key="+" className="w-full" onClick={() => addCourse(semester)}>+</button>
                  </div>}
                </SemesterColumn>
            ))}
            {isDragging && <>
              <SemesterColumn
                key={classesGrid.length }
                semester={classesGrid.length + 1}
                addEnd={(dragCourse: Course & { index: number, semester: number }) => moveCourse(classesGrid.length, dragCourse, 0)}
              />
              <SemesterColumn
                key={classesGrid.length + 1}
                semester={classesGrid.length + 2}
                addEnd={(dragCourse: Course & { index: number, semester: number }) => moveCourse(classesGrid.length + 1, dragCourse, 0)}
              />
            </>}
            </>
        }
      </div>
  )
}

export default PlanBoard
