import ErrorTray from './ErrorTray'
import PlanBoard from './planBoard/PlanBoard'
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
  semester: number
}

const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<ValidatablePlan >({ classes: [], next_semester: 0 })
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
    // make a deep copy of the classes to compare with the next validation
    previousClasses.current = JSON.parse(JSON.stringify(plan.classes))
    setValidanting(false)
  }

  async function addCourse (semIdx: number): Promise<void> {
    const courseCode = prompt('Course code?')
    if (courseCode == null || courseCode === '' || plan?.classes.flat().includes(courseCode.toUpperCase())) return
    setValidanting(true)
    const response = await DefaultService.getCourseDetails([courseCode.toUpperCase()])
    if (response?.status_code === 404) { setValidanting(false); alert(response?.detail); return }
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
    if (!loading) {
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
      {(!loading)
        ? <>
        <div className={'flex flex-col w-5/6'}>

        <ul className={'w-full mb-1 mt-2'}>
            <li className={'inline text-xl ml-3 mr-10 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Titulo:</div> Civil Computación</li>
            <li className={'inline text-xl mr-10 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Major:</div>  Computación - Track Computación</li>
            <li className={'inline text-xl mr-10 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Minor:</div> Eléctrica</li>
          </ul>
          <PlanBoard
            plan={plan}
            courseDetails={courseDetails}
            setPlan={setPlan}
            addCourse={addCourse}
            validating={validating}
          />
        </div>
        <ErrorTray diagnostics={validationDiagnostics} />
        </>
        : <div>Loading</div>}
    </div>
  )
}

export default Planner
