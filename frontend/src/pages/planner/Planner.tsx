import ErrorTray from './ErrorTray'
import PlanBoard from './planBoard/PlanBoard'
import ControlTopBar from './ControlTopBar'
import { useParams } from '@tanstack/react-router'
import { useState, useEffect, useRef } from 'react'
import { DefaultService, FlatDiagnostic, ValidatablePlan, Course, PlanView } from '../../client'
interface EmptyPlan {
  validatable_plan: ValidatablePlan
}
function instanceOfPlanView (object: unknown): object is PlanView {
  if (object != null && typeof object === 'object') {
    return 'id' in object
  }
  return false
}

/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */
const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<PlanView | EmptyPlan>({ validatable_plan: { classes: [], next_semester: 0 } })
  const [courseDetails, setCourseDetails] = useState<{ [code: string]: Course }>({})
  const previousClasses = useRef<string[][]>([['']])
  const [loading, setLoading] = useState(true)
  const [validating, setValidanting] = useState(false)
  const [validationDiagnostics, setValidationDiagnostics] = useState<FlatDiagnostic[]>([])
  const params = useParams()

  async function getDefaultPlan (): Promise<void> {
    console.log('getting Basic Plan...')
    const response: ValidatablePlan = await DefaultService.generatePlan({
      classes: [],
      next_semester: 0,
      level: 1,
      school: 'Ingenieria',
      career: 'Ingenieria'
    })
    await getCourseDetails(response.classes.flat()).catch(err => {
      setValidationDiagnostics([{
        is_warning: false,
        message: `Internal error: ${String(err)}`
      }])
    })
    setPlan({ ...plan, validatable_plan: response })
    await validate(response).catch(err => {
      setValidationDiagnostics([{
        is_warning: false,
        message: `Internal error: ${String(err)}`
      }])
    })
    setLoading(false)
    console.log('data loaded')
  }

  async function getPlanById (id: string): Promise<void> {
    console.log('getting Plan by Id...')
    try {
      const response: PlanView = await DefaultService.readPlan(id)
      setPlan(response)
      await getCourseDetails(response.validatable_plan.classes.flat()).catch(err => {
        setValidationDiagnostics([{
          is_warning: false,
          message: `Internal error: ${String(err)}`
        }])
      })
      await validate(response.validatable_plan).catch(err => {
        setValidationDiagnostics([{
          is_warning: false,
          message: `Internal error: ${String(err)}`
        }])
      })
    } catch (err) {
      alert(err)
      window.location.href = '/planner'
    }
    setLoading(false)
    console.log('data loaded')
  }

  async function getCourseDetails (codes: string[]): Promise<void> {
    setValidanting(true)
    console.log('getting Courses Details...')
    const response: Course[] = await DefaultService.getCourseDetails(codes)
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
    const response = await DefaultService.validatePlan({ ...plan, level: 1, school: 'Ingenieria', career: 'Ingenieria' })
    setValidationDiagnostics(response.diagnostics)
    console.log('validated')
    setValidanting(false)
    // make a deep copy of the classes to compare with the next validation
    previousClasses.current = JSON.parse(JSON.stringify(plan.classes))
  }

  async function savePlan (): Promise<void> {
    if (params?.plannerId != null) {
      setValidanting(true)
      try {
        await DefaultService.updatePlan(params.plannerId, plan.validatable_plan)
        alert('Plan updated successfully')
      } catch (err) {
        alert(err)
      }
    } else {
      const planName = prompt('Nombre de la malla?')
      if (planName == null || planName === '') return
      setValidanting(true)
      try {
        const res = await DefaultService.savePlan(planName, plan.validatable_plan)
        alert('Plan saved successfully')
        window.location.href = `/planner/${res.id}`
      } catch (err) {
        alert(err)
      }
    }
    setValidanting(false)
  }

  async function addCourse (semIdx: number): Promise<void> {
    const courseCode = prompt('Course code?')
    if (courseCode == null || courseCode === '') return
    if (plan.validatable_plan.classes.flat().includes(courseCode.toUpperCase())) { alert(`${courseCode} already on plan`); return }
    setValidanting(true)
    try {
      const response = await DefaultService.getCourseDetails([courseCode.toUpperCase()])
      setCourseDetails((prev) => { return { ...prev, [response[0].code]: response[0] } })
      setPlan((prev) => {
        const newClasses = [...prev.validatable_plan.classes]
        newClasses[semIdx] = [...prev.validatable_plan.classes[semIdx]]
        newClasses[semIdx].push(response[0].code)
        return { ...prev, validatable_plan: { next_semester: prev.validatable_plan.next_semester, classes: newClasses } }
      })
    } catch (err) {
      alert(err)
    }
    setValidanting(false)
  }

  useEffect(() => {
    if (params?.plannerId != null) {
      getPlanById(params.plannerId).catch(err => {
        console.log(err)
      })
    } else {
      getDefaultPlan().catch(err => {
        console.log(err)
      })
    }
  }, [])

  useEffect(() => {
    if (!loading) {
      // dont validate if the classes are rearranging the same semester at previous validation
      if (!plan.validatable_plan.classes.map((sem, index) =>
        JSON.stringify([...sem].sort()) === JSON.stringify(previousClasses.current[index]?.sort())).every(Boolean) ||
         plan.validatable_plan.classes.length !== previousClasses.current.length) {
        validate(plan.validatable_plan).catch(err => {
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
          <ul className={'w-full mb-1 mt-2 relative'}>
            <li className={'inline text-md ml-3 mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Major:</div> Ingeniería y Ciencias Ambientales</li>
            <li className={'inline text-md mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Minor:</div> Amplitud en Programación</li>
            <li className={'inline text-md mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Titulo:</div> Por seleccionar</li>
            {instanceOfPlanView(plan) && <li className={'inline text-md ml-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Plan:</div> {plan.name}</li>}
          </ul>
          <ControlTopBar
            reset={getDefaultPlan}
            save={savePlan}
            validating={validating}
          />
          <PlanBoard
            plan={plan.validatable_plan}
            courseDetails={courseDetails}
            setPlan={setPlan}
            addCourse={addCourse}
            validating={validating}
          />
        </div>
        <ErrorTray diagnostics={validationDiagnostics} validating={validating}/>
        </>
        : <div>Loading</div>}
    </div>
  )
}

export default Planner
