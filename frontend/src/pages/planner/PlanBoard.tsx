import { useState } from 'react'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import SemesterColumn from '../../components/SemesterColumn'
import CourseCard from '../../components/CourseCard'
// import { Course } from '../../lib/types'
/**
 * The main drag-n-drop planner interface.
 * Displays several semesters, as well as several courses per semester.
 *
 * TODO: Reemplazar este mockup temporal por algo de verdad.
 */
const PlanBoard = ({ plan, setPlan }: { plan: string[][], setPlan: Function }): JSX.Element => {
  const [isDragging, setIsDragging] = useState(false)
  function remCourse (semIdx: number, code: string): void {
    const idx = plan[semIdx].indexOf(code)
    if (idx === -1) return
    setPlan((prev: string[][]) => {
      const newPlan = [...prev]
      newPlan[semIdx] = [...prev[semIdx]]
      newPlan[semIdx].splice(idx, 1)
      return newPlan
    })
  }
  function addCourse (semIdx: number): void {
    const courseCode = prompt('Course code?')
    if (courseCode == null || courseCode === '' || plan.flat().includes(courseCode.toUpperCase())) return
    setPlan((prev: string[][]) => {
      const newPlan = [...prev]
      newPlan[semIdx] = [...prev[semIdx]]
      newPlan[semIdx].push(courseCode.toUpperCase())
      return newPlan
    })
  }

  function moveCourse (semester: number, drag: { semester: number, code: string }, code: string): void {
    setPlan((prev: string[][]) => {
      const dragIndex: number = prev[drag.semester].indexOf(drag.code)
      const newPlan = [...prev]
      if (semester - prev.length >= 0) {
        if (semester - prev.length > 0) newPlan.push([])
        newPlan.push([])
      }
      let index = newPlan[semester].indexOf(code)
      if (index === -1) index = newPlan[semester].length
      newPlan[semester].splice(index, 0, drag.code)
      if (semester === drag.semester && index < dragIndex) {
        newPlan[drag.semester].splice(dragIndex + 1, 1)
      } else {
        newPlan[drag.semester].splice(dragIndex, 1)
      }
      while (newPlan[newPlan.length - 1].length === 0) {
        newPlan.pop()
      }
      return newPlan
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
      <div className="CurriculumTable flex flex-row basis-5/6">
        {plan.map((courses: string[], semester: number) => (
            <SemesterColumn key={semester} semester={semester} addEnd={({ course }: any) => moveCourse(semester, course, '')}>
              {courses?.map((code, index: number) => (
                <CourseCard key={code} course={{ code, semester }} isDragging={(e: boolean) => setIsDragging(e)} handleMove={({ course }: any) => moveCourse(semester, course, code)} remCourse={() => remCourse(semester, code)}/>
              ))}
            {!isDragging && <button key="+" className="w-20 h-10 bg-slate-300 text-center" onClick={() => addCourse(semester)}>+</button>}
            </SemesterColumn>
        ))}
        {isDragging && <>
          <SemesterColumn key={plan.length } semester={plan.length } addEnd={({ course }: any) => moveCourse(plan.length, course, '')} />
          <SemesterColumn key={plan.length + 1} semester={plan.length + 1} addEnd={({ course }: any) => moveCourse(plan.length + 1, course, '')} />
        </>}
      </div>
    </DndProvider>
  )
}

export default PlanBoard
