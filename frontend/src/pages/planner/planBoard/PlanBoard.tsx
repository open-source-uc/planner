import { useState } from 'react'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import SemesterColumn from './SemesterColumn'
import CourseCard from './CourseCard'
import { ValidatablePlan, Course } from '../../../client'
/**
 * The main drag-n-drop planner interface.
 * Displays several semesters, as well as several classes per semester.
 */

interface PlanBoardProps {
  plan: ValidatablePlan
  courseDetails: { [code: string]: Course }
  setPlan: Function
  addCourse: Function
  validating: boolean
}

const PlanBoard = ({ plan, courseDetails, setPlan, addCourse, validating }: PlanBoardProps): JSX.Element => {
  const [isDragging, setIsDragging] = useState(false)
  function remCourse (semIdx: number, code: string): void {
    const idx = plan.classes[semIdx].indexOf(code)
    if (idx === -1) return
    setPlan((prev: { validatable_plan: ValidatablePlan }) => {
      const newClasses = [...prev.validatable_plan.classes]
      newClasses[semIdx] = [...prev.validatable_plan.classes[semIdx]]
      newClasses[semIdx].splice(idx, 1)
      while (newClasses[newClasses.length - 1].length === 0) {
        newClasses.pop()
      }
      return { ...prev, validatable_plan: { next_semester: prev.validatable_plan.next_semester, classes: newClasses } }
    })
  }

  function moveCourse (semester: number, drag: Course & { semester: number }, code: string): void {
    setPlan((prev: { validatable_plan: ValidatablePlan }) => {
      const dragIndex: number = prev.validatable_plan.classes[drag.semester].indexOf(drag.code)
      const newClasses = [...prev.validatable_plan.classes]
      if (semester - prev.validatable_plan.classes.length >= 0) {
        if (semester - prev.validatable_plan.classes.length > 0) newClasses.push([])
        newClasses.push([])
      }
      let index = newClasses[semester].indexOf(code)
      if (index === -1) index = newClasses[semester].length
      newClasses[semester].splice(index, 0, drag.code)
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
    <DndProvider backend={HTML5Backend}>
      <div className= {`CurriculumTable overflow-x-auto flex flex-row flex-nowrap rtl-grid ${validating ? 'pointer-events-none' : ''}`}>
        {plan.classes.map((classes: string[], semester: number) => (
            <SemesterColumn
              key={semester}
              semester={semester + 1}
              addEnd={({ course }: any) => moveCourse(semester, course, '')}
            >
              {classes?.map((code: string, index: number) => ((courseDetails?.[code]) != null) && (
                <CourseCard
                  key={code}
                  course={{ ...courseDetails[code], semester }}
                  isDragging={(e: boolean) => setIsDragging(e)}
                  handleMove={({ course }: { course: Course & { semester: number } }) => moveCourse(semester, course, code)}
                  remCourse={() => remCourse(semester, code)}
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
            addEnd={({ course }: { course: Course & { semester: number } }) => moveCourse(plan.classes.length, course, '')}
          />
          <SemesterColumn
            key={plan.classes.length + 1}
            semester={plan.classes.length + 2}
            addEnd={({ course }: { course: Course & { semester: number } }) => moveCourse(plan.classes.length + 1, course, '')}
          />
        </>}
      </div>
    </DndProvider>
  )
}

export default PlanBoard
