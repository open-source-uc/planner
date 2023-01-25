import { useState } from 'react'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import SemesterColumn from './SemesterColumn'
import CourseCard from './CourseCard'
import { ValidatablePlan, Course, ConcreteId, Equivalence, EquivalenceId, FlatValidationResult } from '../../../client'

export type PseudoCourse = ConcreteId | EquivalenceId

interface PlanBoardProps {
  plan: ValidatablePlan
  courseDetails: { [code: string]: Course | Equivalence }
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

const PlanBoard = ({ plan, courseDetails, setPlan, openModal, addCourse, validating, validationResult }: PlanBoardProps): JSX.Element => {
  const [isDragging, setIsDragging] = useState(false)
  function remCourse (semIdx: number, code: string): void {
    let idx = -1
    for (let i = 0; i < plan.classes[semIdx].length; i++) {
      if (plan.classes[semIdx][i].code === code) {
        idx = i
        break
      }
    }
    if (idx === -1) return
    setPlan((prev: { validatable_plan: ValidatablePlan }) => {
      const newClasses = [...prev.validatable_plan.classes]
      newClasses[semIdx] = [...prev.validatable_plan.classes[semIdx]]
      newClasses[semIdx].splice(idx, 1)
      while (newClasses[newClasses.length - 1].length === 0) {
        newClasses.pop()
      }
      return { ...prev, validatable_plan: { ...prev.validatable_plan, classes: newClasses } }
    })
  }

  function moveCourse (semester: number, drag: Course & { semester: number }, index: number): void {
    setPlan((prev: { validatable_plan: ValidatablePlan }) => {
      const dragIndex: number = prev.validatable_plan.classes[drag.semester].findIndex((c: PseudoCourse) => c.code === drag.code)
      const newClasses = [...prev.validatable_plan.classes]
      if (semester - prev.validatable_plan.classes.length >= 0) {
        if (semester - prev.validatable_plan.classes.length > 0) newClasses.push([])
        newClasses.push([])
      }
      newClasses[semester].splice(index, 0, prev.validatable_plan.classes[drag.semester][dragIndex])
      if (semester === drag.semester && index < dragIndex) {
        newClasses[drag.semester].splice(dragIndex + 1, 1)
      } else {
        newClasses[drag.semester].splice(dragIndex, 1)
      }
      while (newClasses[newClasses.length - 1].length === 0) {
        newClasses.pop()
      }
      return { ...prev, validatable_plan: { ...prev.validatable_plan, classes: newClasses } }
    })
  }
  return (
    <DndProvider backend={HTML5Backend}>
      <div className= {`CurriculumTable overflow-x-auto flex flex-row flex-nowrap rtl-grid flex-grow ${validating === true ? 'pointer-events-none' : ''}`}>
        {plan.classes.map((classes: PseudoCourse[], semester: number) => (
            <SemesterColumn
              key={semester}
              semester={semester + 1}
              addEnd={(dragCourse: Course & { semester: number }) => moveCourse(semester, dragCourse, classes.length)}
            >
              {classes?.map((course: PseudoCourse, index: number) => (
                <CourseCard
                  key={index.toString() + course.code}
                  cardData={{ ...courseDetails[course.code], ...course, semester }}
                  isDragging={(e: boolean) => setIsDragging(e)}
                  handleMove={(dragCourse: Course & { semester: number }) => moveCourse(semester, dragCourse, index)}
                  remCourse={() => remCourse(semester, course.code)}
                  courseBlock={findCourseSuperblock(validationResult, course.code)}
                  openSelector={() => { if ('credits' in course) openModal(courseDetails[course.code], semester, index); else openModal(course.equivalence, semester, index) }}
                  hasEquivalence={course.is_concrete === false || ('equivalence' in course && course.equivalence != null)}
                />
              ))}
              {!isDragging && <div className="h-10 mx-2 bg-slate-300 card">
              <button key="+" className="w-full" onClick={() => addCourse(semester)}>+</button>
              </div>}
            </SemesterColumn>
        ))}
        {isDragging && <>
          <SemesterColumn
            key={plan.classes.length }
            semester={plan.classes.length + 1}
            addEnd={(dragCourse: Course & { semester: number }) => moveCourse(plan.classes.length, dragCourse, 0)}
          />
          <SemesterColumn
            key={plan.classes.length + 1}
            semester={plan.classes.length + 2}
            addEnd={(dragCourse: Course & { semester: number }) => moveCourse(plan.classes.length + 1, dragCourse, 0)}
          />
        </>}
      </div>
    </DndProvider>
  )
}

export default PlanBoard
