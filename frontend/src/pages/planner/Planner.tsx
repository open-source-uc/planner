import ErrorTray from './ErrorTray'
import PlanBoard from './PlanBoard'
import { useState, useEffect, useRef } from 'react'
import { DefaultService, Diagnostic, ValidatablePlan } from '../../client'
/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */

export interface Course {
  code: string
  name: string
  credits: number
  deps: JSON
  program: string
  school: string
  area?: string
  category?: string
  semester?: number
}

const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<ValidatablePlan | null>(null)
  const [courseDetails, setCourseDetails] = useState<{ [code: string]: Course }>({})
  const previousClasses = useRef<string[][]>([['']])
  const [loading, setLoading] = useState(true)
  const [validating, setValidanting] = useState(true)
  const [validationDiagnostics, setValidationDiagnostics] = useState<Diagnostic[]>([])

  async function getCourseDetails (codes: string[]): Promise<void> {
    setValidanting(true)
    console.log('getting Courses Details...')
    const response = await DefaultService.getCourseDetails(codes)
    if (response?.status_code === 404) return
    // transform response to dict with key code:
    const dict = response.reduce((acc: { [code: string]: Course }, curr: Course) => {
      acc[curr.code] = curr
      return acc
    }, {})
    setCourseDetails((prev) => { return { ...prev, ...dict } })
    console.log('Details loaded')
    setValidanting(false)
  }

  async function validate (plan: ValidatablePlan): Promise<void> {
    setValidanting(true)
    console.log('validating...')
    const response = await DefaultService.validatePlan(plan)
    setValidationDiagnostics(response.diagnostics)
    console.log('validated')
    setValidanting(false)
  }

  async function addCourse (semIdx: number): Promise<void> {
    const courseCode = prompt('Course code?')
    if (courseCode == null || courseCode === '' || plan?.classes.flat().includes(courseCode.toUpperCase()) === true) return
    const response = await DefaultService.getCourseDetails([courseCode.toUpperCase()])
    if (response?.status_code === 404) return
    setCourseDetails((prev) => { return { ...prev, [response[0].code]: response[0] } })
    setPlan((prev) => {
      const newClasses = [...prev.classes]
      newClasses[semIdx] = [...prev.classes[semIdx]]
      newClasses[semIdx].push(response[0].code)
      return { ...prev, classes: newClasses }
    })
  }

  useEffect(() => {
    const getBasicPlan = async (): Promise<void> => {
      console.log('getting Basic Plan...')
      const response = await DefaultService.generatePlan({
        classes: [],
        next_semester: 1
      })
      setPlan(response)
      await getCourseDetails(response.classes).catch(err => {
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
      // dont validate if the classes are rearranging the same semester at previous validation
      if (!plan.classes.map((sem, index) => JSON.stringify([...sem].sort()) === JSON.stringify(previousClasses.current[index]?.sort())).every(Boolean)) {
        validate(plan).catch(err => {
          setValidationDiagnostics([{
            is_warning: false,
            message: `Internal error: ${String(err)}`
          }])
        })
        // const removedClasses = previousClasses.current.flat().filter(code => !plan.classes.flat().includes(code))
        // if (removedClasses.length > 0) {
        // setCourseDetails((prev) => prev.filter((course: any) => !removedClasses.includes(course.code)))
        // }
      }

      // make a deep copy of the classes to compare with the next validation
      previousClasses.current = JSON.parse(JSON.stringify(plan.classes))
    }
  }, [loading, plan])

  return (
    <div className={`w-full h-full pb-10 flex flex-row border-red-400 border-2 ${validating ? 'cursor-wait' : ''}`}>
      {(!loading && plan != null) ? <PlanBoard plan={plan} courseDetails={courseDetails} setPlan={setPlan} addCourse={addCourse} validating={validating}/> : <div>loading</div>}
      <ErrorTray diagnostics={validationDiagnostics} />
    </div>
  )
}

export default Planner
