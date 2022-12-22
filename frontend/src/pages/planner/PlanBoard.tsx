import { useState, useEffect } from 'react'
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
const PlanBoard = (): JSX.Element => {
  const [plan, setPlan] = useState<string[][]>([['MAT1610', 'QIM100A', 'MAT1203', 'ING1004', 'FIL2001'],
    ['MAT1620', 'FIS1513', 'FIS0151', 'ICS1513', 'IIC1103'],
    ['MAT1630', 'FIS1523', 'FIS0152', 'MAT1640'],
    ['EYP1113', 'FIS1533', 'FIS0153', 'IIC2233'],
    ['IIC2143', 'ING2030', 'IIC1253'],
    ['IIC2113', 'IIC2173', 'IIC2413'],
    ['IIC2133', 'IIC2513', 'IIC2713'],
    ['IIC2154']])
  // por alguna razon se buggea cuando inicia en estado false, asi que se inicia en true y se cambia a false cuando se termina de renderizar. Que asco
  const [isDragging, setIsDragging] = useState(false)
  useEffect(() => {
    console.log(plan)
  }, [plan])
  /*

  function addCourse (semIdx: number): void {
    const courseCode = prompt('Course code?')
    if (courseCode == null) return
    const newPlan = plan.slice()
    newPlan[semIdx] = plan[semIdx].slice()
    newPlan[semIdx].push(courseCode)
    onPlanChange(newPlan)
  }
  function remCourse (semIdx: number, code: string): void {
    const idx = plan[semIdx].indexOf(code)
    if (idx === -1) return
    const newPlan = plan.slice()
    newPlan[semIdx] = plan[semIdx].slice()
    newPlan[semIdx].splice(idx, 1)
    onPlanChange(newPlan)
  }
 */

  function addCourse (semIdx: number): void {
    setPlan(prev => {
      const newPlan = [...prev]
      newPlan[semIdx] = [...prev[semIdx]]
      newPlan[semIdx].push('MAT1610')
      return newPlan
    })
  }

  function moveCourse (semester: number, drag: { semester: number, code: string }, code: string): void {
    setPlan(prev => {
      const dragIndex = prev[drag.semester].indexOf(drag.code)
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
  /* const semUi = plan.map((sem, semIdx) => {
    const courses = sem.map(code => {
      return (
        <button key={code} className="w-20 h-10 bg-blue-300 text-center" onClick={() => remCourse(semIdx, code)}>{code}</button>
      )
    })
    return (
      <div key={semIdx} className="flex flex-col p-2 gap-2 bg-blue-400">
        {courses}
        <button key="+" className="w-20 h-10 bg-slate-300 text-center" onClick={() => addCourse(semIdx)}>+</button>
      </div>
    )
  }) */

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
        {plan.map((courses, semester: number) => (
            <SemesterColumn key={semester} semester={semester} addEnd={({ course }: any) => moveCourse(semester, course, '')}>
              {courses?.map((code, index: number) => (
                <CourseCard key={code} course={{ code, semester }} isDragging={(e: boolean) => setIsDragging(e)} handleMove={({ course }: any) => moveCourse(semester, course, code)}/>
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
