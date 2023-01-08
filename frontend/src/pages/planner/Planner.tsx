import ErrorTray from './ErrorTray'
import PlanBoard from './PlanBoard'
import { useState, useEffect, useRef } from 'react'
import { DefaultService, Diagnostic, ValidatablePlan } from '../../client'
/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */
const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<ValidatablePlan | null>(null)
  const [courseDetails, setCourseDetails] = useState<any>(null)
  const previousClasses = useRef<string[][]>([['']])
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
      if (response != null) {
        const response2 = await DefaultService.getCourseDetails(response?.classes.flat() ?? [''])
        setCourseDetails(response2)
      }
      setLoading(false)
      console.log('data loaded')
    }
    getBasicPlan().catch(err => {
      console.log(err)
    })
  }, [])

  useEffect(() => {
    if (!loading && (plan != null)) {
      // dont validate if the classes are rearranging the same semester at previous validation
      if (!plan.classes.map((sem, index) => JSON.stringify([...sem].sort()) === JSON.stringify(previousClasses.current[index]?.sort())).every(Boolean)) {
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
      // make a deep copy of the classes to compare with the next validation
      previousClasses.current = JSON.parse(JSON.stringify(plan.classes))
    }
  }, [loading, plan])

  return (
    <div className={`w-full  flex flex-row border-red-400 border-2 ${validating ? 'cursor-wait' : ''}`}>
      {(!loading && plan != null) ? <PlanBoard plan={plan} courseDetails={courseDetails} setPlan={setPlan} validating={validating}/> : <div>loading</div>}
      <ErrorTray diagnostics={validationDiagnostics} />
    </div>
  )
}

export default Planner
