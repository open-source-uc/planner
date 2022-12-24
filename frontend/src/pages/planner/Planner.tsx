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
  const [validationDiagnostics, setValidationDiagnostics] = useState<Diagnostic[]>([])
  console.log(plan)
  useEffect(() => {
    const getBasicPlan = async (): Promise<void> => {
      console.log('getting Basic Plan...')
      const response = await DefaultService.generatePlan({
        classes: [[]],
        next_semester: -1
      })
      console.log(response)
      // TODO save response to local storage
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
      const validate = async (): Promise<void> => {
        console.log('validating...')
        console.log(plan)
        const response = await DefaultService.validatePlan(plan)
        setValidationDiagnostics(response.diagnostics)
        console.log('validated')
      }
      validate().catch(err => {
        setValidationDiagnostics([{
          is_warning: false,
          message: `Internal error: ${String(err)}`
        }])
      })
    }
  }, [loading, plan])

  return (
    <div className="w-full h-full overflow-hidden flex flex-row justify-items-stretch border-red-400 border-2">
      {(plan != null && !loading) ? <PlanBoard plan={plan} setPlan={setPlan}/> : <div>loading data</div>}
      <ErrorTray diagnostics={validationDiagnostics} />
    </div>
  )
}

export default Planner
