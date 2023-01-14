import ErrorTray from './ErrorTray'
import PlanBoard from './planBoard/PlanBoard'
import { useState, useEffect, useRef } from 'react'
import { DefaultService, FlatDiagnostic, ValidatablePlan, Course } from '../../client'
/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */

const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<ValidatablePlan >({ classes: [], next_semester: 0 })
  const [courseDetails, setCourseDetails] = useState<{ [code: string]: Course }>({})
  const previousClasses = useRef<string[][]>([['']])
  const [loading, setLoading] = useState(true)
  const [validating, setValidanting] = useState(false)
  const [validationDiagnostics, setValidationDiagnostics] = useState<FlatDiagnostic[]>([])

  async function getCourseDetails (codes: string[]): Promise<void> {
    setValidanting(true)
    console.log('getting Courses Details...')
    const response = await DefaultService.getCourseDetails(codes)
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
    if (courseCode == null || courseCode === '') return
    if (plan?.classes.flat().includes(courseCode.toUpperCase())) { alert(`${courseCode} already on plan`); return }
    setValidanting(true)
    try {
      const response = await DefaultService.getCourseDetails([courseCode.toUpperCase()])
      setCourseDetails((prev) => { return { ...prev, [response[0].code]: response[0] } })
      setPlan((prev) => {
        const newClasses = [...prev.classes]
        newClasses[semIdx] = [...prev.classes[semIdx]]
        newClasses[semIdx].push(response[0].code)
        return { ...prev, classes: newClasses }
      })
    } catch (err) {
      alert(err)
    }
    setValidanting(false)
  }

  useEffect(() => {
    const getBasicPlan = async (): Promise<void> => {
      console.log('getting Basic Plan...')
      const response = await DefaultService.generatePlan({
        classes: [],
        next_semester: 0,
        level: 1,
        school: 'Ingenieria',
        career: 'Ingenieria'
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
            <li className={'inline text-md ml-3 mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Titulo:</div> Civil de Industrias, Diploma en Ingeniería de Computación</li>
            <li className={'inline text-md mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Major:</div> Ingeniería y Ciencias Ambientales</li>
            <li className={'inline text-md mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Minor:</div> Amplitud en Programación</li>
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
