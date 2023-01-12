import ErrorTray from './ErrorTray'
import PlanBoard from './planBoard/PlanBoard'
import ControlTopBar from './ControlTopBar'
import { useParams } from '@tanstack/react-router'
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

export interface PlanDetails {
  id: string
  created_at: Date
  updated_at: Date
  name: string
  user_rut: string
  validatable_plan: ValidatablePlan
}

const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<PlanDetails | { validatable_plan: ValidatablePlan }>({ validatable_plan: { classes: [], next_semester: 1 } })
  const [courseDetails, setCourseDetails] = useState<{ [code: string]: Course }>({})
  const previousClasses = useRef<string[][]>([['']])
  const [loading, setLoading] = useState(true)
  const [validating, setValidanting] = useState(true)
  const [validationDiagnostics, setValidationDiagnostics] = useState<Diagnostic[]>([])
  const params = useParams()

  async function getDefaultPlan (): Promise<void> {
    console.log('getting Basic Plan...')
    const response = await DefaultService.generatePlan({
      classes: [],
      next_semester: 1
    })
    setPlan({ validatable_plan: response })
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

  async function getPlanById (id: string): Promise<void> {
    console.log('getting Plan by Id...')
    const response = await DefaultService.readPlan(id)
    setPlan(response)
    await getCourseDetails(response.validatable_plan.classes).catch(err => {
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
    setLoading(false)
    console.log('data loaded')
  }

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

  async function savePlan (): Promise<void> {
    if (params?.plannerId != null) {
      setValidanting(true)
      try {
        await DefaultService.updatePlan(params.plannerId, plan?.validatable_plan)
        alert('Plan updated successfully')
      } catch (err) {
        alert(err)
      }
      setValidanting(false)
    } else {
      const planName = prompt('Nombre de la malla?')
      if (planName == null || planName === '') return
      setValidanting(true)
      try {
        const res = await DefaultService.savePlan(planName, plan?.validatable_plan)
        alert('Plan saved successfully')
        window.location.href = `/planner/${res.id}`
      } catch (err) {
        alert(err)
      }
      setValidanting(false)
    }
  }
  async function erasePlan (): Promise<void> {
    setValidanting(true)
    if (params?.plannerId != null) {
      try {
        await DefaultService.deletePlan(params?.plannerId)
        alert('Plan erased successfully')
        window.location.href = '/'
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
    const response = await DefaultService.getCourseDetails([courseCode.toUpperCase()])
    if (response?.status_code === 404) { setValidanting(false); alert(response?.detail); return }
    setCourseDetails((prev) => { return { ...prev, [response[0].code]: response[0] } })
    setPlan((prev) => {
      const newClasses = [...prev.validatable_plan.classes]
      newClasses[semIdx] = [...prev.validatable_plan.classes[semIdx]]
      newClasses[semIdx].push(response[0].code)
      return { ...prev, validatable_plan: { next_semester: prev.validatable_plan.next_semester, classes: newClasses } }
    })
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
      if (!plan.validatable_plan.classes.map((sem, index) => JSON.stringify([...sem].sort()) === JSON.stringify(previousClasses.current[index]?.sort())).every(Boolean)) {
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
          <ul className={'w-full mb-1 mt-2 relative '}>
            <li className={'inline text-xl ml-3 mr-10 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Titulo:</div> Civil Computación</li>
            <li className={'inline text-xl mr-10 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Major:</div>  Computación - Track Computación</li>
            <li className={'inline text-xl mr-10 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Minor:</div> Eléctrica</li>
            <li className={'inline text-2xl ml-40 font-bold absolute'}>{plan?.name}</li>
          </ul>
          <ControlTopBar
            reset={getDefaultPlan}
            save={savePlan}
            erase={erasePlan}
            validating={validating}
          />
          <PlanBoard
            plan={plan?.validatable_plan}
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
