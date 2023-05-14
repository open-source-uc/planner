import { useState } from 'react'
import SemesterColumn from './SemesterColumn'
import CourseCard from './CourseCard'
import { ValidatablePlan, Course, FlatValidationResult } from '../../../client'
import { PseudoCourseId, PseudoCourseDetail } from '../Planner'

interface PlanBoardProps {
  classesGrid: PseudoCourseId[][] | null
  classesDetails: { [code: string]: PseudoCourseDetail }
  setPlan: Function
  openModal: Function
  addCourse: Function
  validating: Boolean
  validationResult: FlatValidationResult | null
}

const findCourseSuperblock = (validationResults: FlatValidationResult | null, code: string): string | null => {
  if (validationResults == null) return null
  for (const c in validationResults.course_superblocks) {
    if (c === code) return validationResults.course_superblocks[c].normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(' ', '').split(' ')[0]
  }
  return null
}

/**
 * The main drag-n-drop planner interface.
 * Displays several semesters, as well as several classes per semester.
 */

const PlanBoard = ({ classesGrid, classesDetails, setPlan, openModal, addCourse, validating, validationResult }: PlanBoardProps): JSX.Element => {
  const [isDragging, setIsDragging] = useState(false)
  function remCourse (semIdx: number, code: string): void {
    let idx = -1
    for (let i = 0; i < classesGrid[semIdx].length; i++) {
      if (classesGrid[semIdx][i].code === code) {
        idx = i
        break
      }
    }
    if (idx === -1) return
    setPlan((prev: ValidatablePlan) => {
      const newClasses = [...prev.classes]
      newClasses[semIdx] = [...prev.classes[semIdx]]
      newClasses[semIdx].splice(idx, 1)
      while (newClasses[newClasses.length - 1].length === 0) {
        newClasses.pop()
      }
      return { ...prev, classes: newClasses }
    })
  }

  function moveCourse (semester: number, drag: Course & { semester: number }, index: number): void {
    setPlan((prev: ValidatablePlan) => {
      const dragIndex: number = prev.classes[drag.semester].findIndex((c: PseudoCourseId) => c.code === drag.code)
      const newClasses = [...prev.classes]
      if (semester - prev.classes.length >= 0) {
        if (semester - prev.classes.length > 0) newClasses.push([])
        newClasses.push([])
      }
      newClasses[semester].splice(index, 0, prev.classes[drag.semester][dragIndex])
      if (semester === drag.semester && index < dragIndex) {
        newClasses[drag.semester].splice(dragIndex + 1, 1)
      } else {
        newClasses[drag.semester].splice(dragIndex, 1)
      }
      while (newClasses[newClasses.length - 1].length === 0) {
        newClasses.pop()
      }
      return { ...prev, classes: newClasses }
    })
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
                  addEnd={(dragCourse: Course & { semester: number }) => moveCourse(semester, dragCourse, classes.length)}
                >
                  {classes?.map((course: PseudoCourseId, index: number) => (
                    <CourseCard
                      key={index.toString() + course.code}
                      cardData={{ ...course, semester, ...classesDetails[course.code] }}
                      isDragging={(e: boolean) => setIsDragging(e)}
                      handleMove={(dragCourse: Course & { semester: number }) => moveCourse(semester, dragCourse, index)}
                      remCourse={() => remCourse(semester, course.code)}
                      courseBlock={findCourseSuperblock(validationResult, course.code)}
                      openSelector={() => { if ('credits' in course) openModal(course, semester, index); else openModal(course.equivalence, semester, index) }}
                      hasEquivalence={course.is_concrete === false || ('equivalence' in course && course.equivalence != null)}
                      hasError={validationResult?.diagnostics?.find((e) => e.course_code === course.code && !e.is_warning) != null}
                      hasWarning={validationResult?.diagnostics?.find((e) => e.course_code === course.code && e.is_warning) != null}
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
                addEnd={(dragCourse: Course & { semester: number }) => moveCourse(classesGrid.length, dragCourse, 0)}
              />
              <SemesterColumn
                key={classesGrid.length + 1}
                semester={classesGrid.length + 2}
                addEnd={(dragCourse: Course & { semester: number }) => moveCourse(classesGrid.length + 1, dragCourse, 0)}
              />
            </>}
            </>
        }
      </div>
  )
}

export default PlanBoard
