import { Spinner } from '../../components/Spinner'
import ErrorTray from './ErrorTray'
import PlanBoard from './planBoard/PlanBoard'
import ControlTopBar from './ControlTopBar'
import { useParams } from '@tanstack/react-router'
import { useState, useEffect, useRef } from 'react'
import { DefaultService, ValidatablePlan, Course, ConcreteId, EquivalenceId, FlatValidationResult, PlanView } from '../../client'

type PseudoCourse = ConcreteId | EquivalenceId

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
  const previousClasses = useRef<PseudoCourse[][]>([[]])
  const [loading, setLoading] = useState(true)
  const [validating, setValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<FlatValidationResult | null>(null)
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
    console.log(response)
    await getCourseDetails(response.classes.flat()).catch(err => {
      setValidationResult({
        diagnostics: [{
          is_warning: false,
          message: `Internal error: ${String(err)}`
        }],
        course_superblocks: {}
      })
    })
    setPlan({ ...plan, validatable_plan: response })
    await validate(response).catch(err => {
      setValidationResult({
        diagnostics: [{
          is_warning: false,
          message: `Internal error: ${String(err)}`
        }],
        course_superblocks: {}
      })
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
        setValidationResult({
          diagnostics: [{
            is_warning: false,
            message: `Internal error: ${String(err)}`
          }],
          course_superblocks: {}
        })
      })
      await validate(response.validatable_plan).catch(err => {
        setValidationResult({
          diagnostics: [{
            is_warning: false,
            message: `Internal error: ${String(err)}`
          }],
          course_superblocks: {}
        })
      })
    } catch (err) {
      alert(err)
      window.location.href = '/planner'
    }
    setLoading(false)
    console.log('data loaded')
  }

  async function getCourseDetails (courses: PseudoCourse[]): Promise<void> {
    setValidating(true)
    console.log('getting Courses Details...')
    const codes = []
    for (const courseid of courses) {
      if (courseid.is_concrete === true) { codes.push(courseid.code) }
    }
    const response = await DefaultService.getCourseDetails(codes)
    // transform response to dict with key code:
    const dict = response.reduce((acc: { [code: string]: Course }, curr: Course) => {
      acc[curr.code] = curr
      return acc
    }, {})
    setCourseDetails((prev) => { return { ...prev, ...dict } })
    setValidating(false)
  }

  async function validate (validatablePlan: ValidatablePlan): Promise<void> {
    setValidating(true)
    const response = await DefaultService.validatePlan(validatablePlan)
    setValidationResult(response)
    setValidating(false)
    // Es necesario hacer una copia profunda del plan para comparar, pues si se copia el objeto entero
    // entonces la copia es modificada junto al objeto original. Lo ideal seria usar una librearia para esto en el futuro
    previousClasses.current = JSON.parse(JSON.stringify(validatablePlan.classes))
  }

  async function savePlan (): Promise<void> {
    if (params?.plannerId != null) {
      setValidating(true)
      try {
        await DefaultService.updatePlan(params.plannerId, plan.validatable_plan)
        alert('Plan actualizado exitosamente.')
      } catch (err) {
        alert(err)
      }
    } else {
      const planName = prompt('¿Cómo quieres llamarle a esta planificación?')
      if (planName == null || planName === '') return
      setValidating(true)
      try {
        const res = await DefaultService.savePlan(planName, plan.validatable_plan)
        alert('Plan guardado exitosamente.')
        window.location.href = `/planner/${res.id}`
      } catch (err) {
        alert(err)
      }
    }
    setValidating(false)
  }

  async function addCourse (semIdx: number): Promise<void> {
    const courseCodeRaw = prompt('Sigla del curso?')
    if (courseCodeRaw == null || courseCodeRaw === '') return
    const courseCode = courseCodeRaw.toUpperCase()
    for (const existingCourse of plan?.validatable_plan.classes.flat()) {
      if (existingCourse.code === courseCode) {
        alert(`${courseCode} ya se encuentra en el plan`)
        return
      }
    }
    setValidating(true)
    try {
      const response = await DefaultService.getCourseDetails([courseCode])
      setCourseDetails((prev) => { return { ...prev, [response[0].code]: response[0] } })
      setPlan((prev) => {
        const newClasses = [...prev.validatable_plan.classes]
        newClasses[semIdx] = [...prev.validatable_plan.classes[semIdx]]
        newClasses[semIdx].push({
          is_concrete: true,
          code: response[0].code
        })
        return { ...prev, validatable_plan: { ...prev.validatable_plan, next_semester: prev.validatable_plan.next_semester, classes: newClasses } }
      })
    } catch (err) {
      alert(err)
    }
    setValidating(false)
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
      let changed = plan.validatable_plan.classes.length !== previousClasses.current.length
      if (!changed) {
        console.log()
        for (let idx = 0; idx < plan.validatable_plan.classes.length; idx++) {
          const cur = [...plan.validatable_plan.classes[idx]].sort((a, b) => a.code.localeCompare(b.code))
          const prev = [...previousClasses.current[idx]].sort((a, b) => a.code.localeCompare(b.code))
          if (JSON.stringify(cur) !== JSON.stringify(prev)) {
            changed = true
            break
          }
        }
      }
      if (changed) {
        validate(plan.validatable_plan).catch(err => {
          setValidationResult({
            diagnostics: [{
              is_warning: false,
              message: `Internal error: ${String(err)}`
            }],
            course_superblocks: {}
          })
        })
      }
    }
  }, [loading, plan])
  return (
    <div className={`w-full h-full p-3 pb-10 flex flex-row border-2 ${validating ? 'cursor-wait' : ''}`}>
      {(!loading)
        ? <>
        <div className={'flex flex-col w-5/6'}>
          <ul className={'w-full mb-3 mt-2 relative'}>
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
            validationResult={validationResult}
          />
        </div>
        <ErrorTray diagnostics={validationResult?.diagnostics ?? []} validating={validating}/>
        </>
        : <Spinner message='Cargando...' />}
    </div>
  )
}

export default Planner
