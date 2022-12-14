
const PlannerStudio = ({ plan, onPlanChange }: { plan: string[][], onPlanChange: (plan: string[][]) => void }): JSX.Element => {
  const options: Array<[string, string[][]]> = [
    ['Resetear malla', []],
    ['Plan comun', [['MAT1610', 'MAT1203', 'QIM100E', 'ING1004', 'FIL2001'], ['MAT1620', 'ICE1514', 'ICS1513', 'IIC1103', 'TTF058']]]
  ]
  const buttons = options.map(btndata => {
    const [name, plan] = btndata
    return (
      <button className="w-40 h-10 rounded-md bg-slate-700 text-white" onClick={() => onPlanChange(plan)} key={name}>
        {name}
      </button>
    )
  })
  return (
    <div className="flex-1 flex flex-col justify-center items-center gap-2 border border-blue-600">
      Aca va el planner.
      {buttons}
    </div>
  )
}

export default PlannerStudio
