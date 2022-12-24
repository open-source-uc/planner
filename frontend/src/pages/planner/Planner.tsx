import ErrorTray from './ErrorTray'
import PlanBoard from './PlanBoard'
import { useState, useEffect } from 'react'
import { DefaultService, Diagnostic, ValidatablePlan } from '../../client'
/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */
const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<ValidatablePlan | null>(null)
  const [loading, setLoading] = useState(true)
  const [validating, setValidanting] = useState(false)
  const [validationDiagnostics, setValidationDiagnostics] = useState<Diagnostic[]>([])

  useEffect(() => {
    const getBasicPlan = async (): Promise<void> => {
      console.log('getting Basic Plan...')
      const response = await DefaultService.generatePlan({
        classes: [],
        next_semester: 1
      })

      setPlan(response)
      setLoading(false)
      console.log('data loaded')
    }
    getBasicPlan().catch(err => {
      console.log(err)
    })
  }, [])

  useEffect(() => {
    if (!loading && (plan != null)) {
      setValidanting(true)
      const validate = async (): Promise<void> => {
        console.log('validating...')
        const response = await DefaultService.validatePlan(plan)
        setValidationDiagnostics(response.diagnostics)
        setValidanting(false)
        console.log('validated')
      }
      validate().catch(err => {
        setValidationDiagnostics([{
          is_warning: false,
          message: `Internal error: ${String(err)}`
        }])
      })
    }
    // to avoid changes in plan while running validation, we should add plan to the dependency array
  }, [loading, plan])

  return (
    <div className={`w-full h-full overflow-hidden flex flex-row justify-items-stretch border-red-400 border-2 ${validating ? 'cursor-wait' : ''}`}>
      {(!loading && plan != null) ? <PlanBoard plan={plan} setPlan={setPlan} validating={validating}/> : <div>loading</div>}
      <ErrorTray diagnostics={validationDiagnostics} />
    </div>
  )
}

export default Planner
