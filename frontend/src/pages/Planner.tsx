import ErrorTray from './ErrorTray'
import PlannerStudio from './PlannerStudio'
import { useState, useEffect } from 'react'
import { DefaultService, Diagnostic } from '../client'

const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<string[][]>([['MAT1610'], ['MAT1620'], ['MAT1630'], ['IEE1513'], ['IIC2233'], []])
  const [validationDiagnostics, setValidationDiagnostics] = useState<Diagnostic[]>([])

  useEffect(() => {
    const validate = async (): Promise<void> => {
      console.log('validating...')
      const response = await DefaultService.validatePlan({
        classes: plan,
        next_semester: 1
      })
      setValidationDiagnostics(response.diagnostics)
      console.log('validated')
    }
    validate().catch(err => {
      setValidationDiagnostics([err.toString()])
    })
  }, [plan])

  return (
    <div className="w-full h-full overflow-hidden flex flex-row justify-items-stretch border-red-400 border-2">
      <PlannerStudio plan={plan} onPlanChange={setPlan} />
      <ErrorTray diagnostics={validationDiagnostics} />
    </div>
  )
}

export default Planner
