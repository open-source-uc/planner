import { useState } from 'react'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import SemesterColumn from './SemesterColumn'
import CourseCard from './CourseCard'
import { ValidatablePlan } from '../../client'
/**
 * The main drag-n-drop planner interface.
 * Displays several semesters, as well as several classes per semester.
 *
 * TODO: Reemplazar este mockup temporal por algo de verdad.
 */
const PlanBoard = ({ plan, setPlan, validating }: { plan: ValidatablePlan, setPlan: Function, validating: Boolean }): JSX.Element => {
  const [isDragging, setIsDragging] = useState(false)
  function remCourse (semIdx: number, code: string): void {
    const idx = plan.classes[semIdx].indexOf(code)
    if (idx === -1) return
    setPlan((prev: { classes: string[][] }) => {
      const newClasses = [...prev.classes]
      newClasses[semIdx] = [...prev.classes[semIdx]]
      newClasses[semIdx].splice(idx, 1)
      return { ...prev, classes: newClasses }
    })
  }
  function addCourse (semIdx: number): void {
    const courseCode = prompt('Course code?')
    if (courseCode == null || courseCode === '' || plan.classes.flat().includes(courseCode.toUpperCase())) return
    setPlan((prev: string[][]) => {
      const newClasses = [...plan.classes]
      newClasses[semIdx] = [...plan.classes[semIdx]]
      newClasses[semIdx].push(courseCode.toUpperCase())
      return { ...prev, classes: newClasses }
    })
  }

  function moveCourse (semester: number, drag: { semester: number, code: string }, code: string): void {
    setPlan((prev: { classes: string[][] }) => {
      const dragIndex: number = prev.classes[drag.semester].indexOf(drag.code)
      const newClasses = [...prev.classes]
      if (semester - prev.classes.length >= 0) {
        if (semester - prev.classes.length > 0) newClasses.push([])
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

  /* const options: Array<[string, string[][]]> = [
    ['Resetear malla', []],
    ['Plan comun (sin lab de dinamica)', [['MAT1610', 'MAT1203', 'QIM100E', 'ING1004', 'FIL2001'], ['MAT1620', 'ICE1514', 'ICS1513', 'IIC1103', 'TTF058']]],
    ['Plan comun', [['MAT1610', 'MAT1203', 'QIM100E', 'ING1004', 'FIL2001'], ['MAT1620', 'ICE1514', 'ICS1513', 'FIS0154', 'IIC1103', 'TTF058']]]
  ]
  const buttons = options.map(btndata => {
    const [name, plan] = btndata
    return (
      <button className="w-40 h-10 rounded-md bg-slate-700 text-white" onClick={() => onPlanChange(plan)} key={name}>
        {name}
      </button>
    )
  }) */

  return (
    <DndProvider backend={HTML5Backend}>
      <div className= {`CurriculumTable flex flex-row basis-5/6 ${validating === true ? 'pointer-events-none' : ''}`}>
        {plan.classes.map((classes: string[], semester: number) => (
            <SemesterColumn key={semester} semester={semester + 1} addEnd={({ course }: any) => moveCourse(semester, course, '')}>
              {classes?.map((code, index: number) => (
                <CourseCard key={code} course={{ code, semester }} isDragging={(e: boolean) => setIsDragging(e)} handleMove={({ course }: any) => moveCourse(semester, course, code)} remCourse={() => remCourse(semester, code)}/>
              ))}
            {!isDragging && <button key="+" className="w-20 h-10 bg-slate-300 text-center" onClick={() => addCourse(semester)}>+</button>}
            </SemesterColumn>
        ))}
        {isDragging && <>
          <SemesterColumn key={plan.classes.length } semester={plan.classes.length + 1} addEnd={({ course }: any) => moveCourse(plan.classes.length, course, '')} />
          <SemesterColumn key={plan.classes.length + 1} semester={plan.classes.length + 2} addEnd={({ course }: any) => moveCourse(plan.classes.length + 1, course, '')} />
        </>}
      </div>
    </DndProvider>
  )
}

export default PlanBoard
