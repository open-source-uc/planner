
const PlannerStudio = ({ plan, onPlanChange }: { plan: string[][], onPlanChange: (plan: string[][]) => void }): JSX.Element => {
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

  const semUi = plan.map((sem, semIdx) => {
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
  })

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
    <div className="flex-1 flex flex-row justify-center items-center gap-2 border border-blue-600">
      {semUi}
    </div>
  )
}

export default PlannerStudio
