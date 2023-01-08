import ErrorTray from './ErrorTray'
import PlanBoard from './PlanBoard'
import { useState, useEffect, useRef } from 'react'
import { DefaultService, Diagnostic, ValidatablePlan } from '../../client'
/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */
const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<ValidatablePlan | null>(null)
  const [courseDetails, setCourseDetails] = useState<any>([])
  const previousClasses = useRef<string[][]>([['']])
  const [loading, setLoading] = useState(true)
  const [validating, setValidanting] = useState(false)
  const [validationDiagnostics, setValidationDiagnostics] = useState<Diagnostic[]>([])

  async function getCourseDetails (codes: string[]): Promise<void> {
    console.log('getting Courses Details...')
    const response = await DefaultService.getCourseDetails(codes)
    if (response?.status_code === 404) return
    setCourseDetails((prev) => { return [...prev, ...response] })
    console.log('Details loaded')
  }

  async function validate (plan: ValidatablePlan): Promise<void> {
    console.log('validating...')
    setValidanting(true)
    const response = await DefaultService.validatePlan(plan)
    setValidationDiagnostics(response.diagnostics)
    setValidanting(false)
    console.log('validated')
    // make a deep copy of the classes to compare with the next validation
    previousClasses.current = JSON.parse(JSON.stringify(plan.classes))
  }

  useEffect(() => {
    const getBasicPlan = async (): Promise<void> => {
      console.log('getting Basic Plan...')
      const response = await DefaultService.generatePlan({
        classes: [],
        next_semester: 1
      })
      setPlan(response)
      await getCourseDetails(response.classes.flat() ?? ['']).catch(err => {
        setValidationDiagnostics([{
          is_warning: false,
          message: `Internal error: ${String(err)}`
        }])
      })
      await validate(response).catch(err => {
        setValidationDiagnostics([{
          is_warning: false,
          message: `Internal error: ${String(err)}`
        }])
      })
      setLoading(false)
      console.log('data loaded')
    }
    getBasicPlan().catch(err => {
      console.log(err)
    })
  }, [])

  useEffect(() => {
    if (!loading && (plan != null)) {
      // get all classes that differ from the previous validation
      const addedClasses = plan.classes.map((sem, index) => [...sem].filter(code => !previousClasses.current[index]?.includes(code))).flat()
      if (addedClasses.length > 0) {
        getCourseDetails(addedClasses).catch(err => {
          setValidationDiagnostics([{
            is_warning: false,
            message: `Internal error: ${String(err)}`
          }])
        })
      }
      const removedClasses = previousClasses.current.map((sem, index) => [...sem].filter(code => !plan.classes[index]?.includes(code))).flat()
      console.log(addedClasses, removedClasses)
      // dont validate if the classes are rearranging the same semester at previous validation
      if (!plan.classes.map((sem, index) => JSON.stringify([...sem].sort()) === JSON.stringify(previousClasses.current[index]?.sort())).every(Boolean)) {
        validate(plan).catch(err => {
          setValidationDiagnostics([{
            is_warning: false,
            message: `Internal error: ${String(err)}`
          }])
        })
      }
    }
  }, [loading, plan])

  return (
    <div className={`w-full h-full pb-10 flex flex-row border-red-400 border-2 ${validating ? 'cursor-wait' : ''}`}>
      {(!loading && plan != null) ? <PlanBoard plan={plan} courseDetails={courseDetails} setPlan={setPlan} validating={validating}/> : <div>loading</div>}
      <ErrorTray diagnostics={validationDiagnostics} />
    </div>
  )
}

export default Planner
