import { Spinner } from '../../components/Spinner'
import ErrorTray from './ErrorTray'
import PlanBoard from './planBoard/PlanBoard'
import ControlTopBar from './ControlTopBar'
import CourseSelectorDialog from '../../components/CourseSelectorDialog'
import { useParams } from '@tanstack/react-router'
import { useState, useEffect, useRef } from 'react'
import { ApiError, DefaultService, ValidatablePlan, Course, Equivalence, ConcreteId, EquivalenceId, FlatValidationResult, PlanView } from '../../client'
import { useAuth } from '../../contexts/auth.context'
import { toast } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
type PseudoCourse = ConcreteId | EquivalenceId

type ModalData = { equivalence: Equivalence, semester: number, index: number } | undefined

interface PlanWithNoOwner {
  validatable_plan: ValidatablePlan
}
type Status = 'loading' | 'validating' | 'ready' | 'error'

const isApiError = (err: any): err is ApiError => {
  return err.status !== undefined
}
/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */
const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<PlanView | PlanWithNoOwner | null>(null)
  const [courseDetails, setCourseDetails] = useState<{ [code: string]: Course | Equivalence }>({})
  const [modalData, setModalData] = useState<ModalData>()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const previousClasses = useRef<PseudoCourse[][]>([[]])
  const [status, setStatus] = useState<Status>('loading')
  const [validationResult, setValidationResult] = useState<FlatValidationResult | null>(null)
  const [error, setError] = useState<String | null>(null)
  const params = useParams()
  const authState = useAuth()

  function handleErrors (err: unknown): void {
    console.log(err)
    setStatus('error')
    if (isApiError(err)) {
      switch (err.status) {
        case 401:
          console.log('token invalid or expired, loading re-login page')
          toast.error('Token invalido. Redireccionando a pagina de inicio...')
          break
        case 403:
          toast.warn('No tienes permisos para realizar esa accion')
          break
        case 404:
          setError('El planner al que estas intentando acceder no existe o no es de tu propiedad')
          break
        case 500:
          setError(err.message)
          break
        default:
          console.log(err.status)
          setError('error desconocido')
          break
      }
    } else {
      setError('error desconocido')
    }
  }

  async function getDefaultPlan (): Promise<void> {
    try {
      setStatus('loading')
      console.log('getting Basic Plan...')
      const basePlan = authState?.user == null ? await DefaultService.emptyGuestPlan() : await DefaultService.emptyPlanForUser()
      const response: ValidatablePlan = await DefaultService.generatePlan(basePlan)
      await Promise.all([
        validate(response),
        getCourseDetails(response.classes.flat())
      ])
      setStatus('ready')
      setPlan(prevPlan => ({ ...prevPlan, validatable_plan: response }))
      console.log('data loaded')
    } catch (err) {
      handleErrors(err)
    }
  }

  async function getPlanById (id: string): Promise<void> {
    try {
      setStatus('loading')
      console.log('getting Plan by Id...')
      const response: PlanView = await DefaultService.readPlan(id)
      await Promise.all([
        validate(response.validatable_plan),
        getCourseDetails(response.validatable_plan.classes.flat())
      ])
      setPlan(response)
      setStatus('ready')
      console.log('data loaded')
    } catch (err) {
      handleErrors(err)
    }
  }

  async function getCourseDetails (courses: PseudoCourse[]): Promise<void> {
    console.log('getting Courses Details...')
    const coursesCodes = []
    const equivalenceCodes = []
    for (const courseid of courses) {
      if (courseid.is_concrete === true) { coursesCodes.push(courseid.code) } else { equivalenceCodes.push(courseid.code) }
    }
    try {
      const promises = []
      if (coursesCodes.length > 0) promises.push(DefaultService.getCourseDetails(coursesCodes))
      if (equivalenceCodes.length > 0) promises.push(DefaultService.getEquivalenceDetails(equivalenceCodes))
      const courseDetails = await Promise.all(promises)
      const dict = courseDetails.flat().reduce((acc: { [code: string]: Course | Equivalence }, curr: Course | Equivalence) => {
        acc[curr.code] = curr
        return acc
      }, {})
      setCourseDetails((prev) => { return { ...prev, ...dict } })
    } catch (err) {
      handleErrors(err)
    }
  }

  async function validate (validatablePlan: ValidatablePlan): Promise<void> {
    try {
      const response = authState?.user == null ? await DefaultService.validateGuestPlan(validatablePlan) : await DefaultService.validatePlanForUser(validatablePlan)
      setValidationResult(response)
      setStatus('ready')
      // Es necesario hacer una copia profunda del plan para comparar, pues si se copia el objeto entero
      // entonces la copia es modificada junto al objeto original. Lo ideal seria usar una librearia para esto en el futuro
      previousClasses.current = JSON.parse(JSON.stringify(validatablePlan.classes))
    } catch (err) {
      handleErrors(err)
    }
  }

  async function savePlan (): Promise<void> {
    if (plan == null) {
      alert('No se ha generado un plan aun')
      return
    }
    if (params?.plannerId != null) {
      setStatus('validating')
      try {
        await DefaultService.updatePlan(params.plannerId, plan.validatable_plan)
        alert('Plan actualizado exitosamente.')
      } catch (err) {
        handleErrors(err)
      }
    } else {
      const planName = prompt('¿Cómo quieres llamarle a esta planificación?')
      if (planName == null || planName === '') return
      setStatus('validating')
      try {
        const res = await DefaultService.savePlan(planName, plan.validatable_plan)
        alert('Plan guardado exitosamente.')
        window.location.href = `/planner/${res.id}`
      } catch (err) {
        handleErrors(err)
      }
    }
    setStatus('ready')
  }

  async function addCourse (semIdx: number): Promise<void> {
    if (plan == null) {
      return
    }
    const courseCodeRaw = prompt('Sigla del curso?')
    if (courseCodeRaw == null || courseCodeRaw === '') return
    const courseCode = courseCodeRaw.toUpperCase()
    for (const existingCourse of plan?.validatable_plan.classes.flat()) {
      if (existingCourse.code === courseCode) {
        alert(`${courseCode} ya se encuentra en el plan, seleccione otro curso por favor`)
        return
      }
    }
    setStatus('validating')
    try {
      const response = await DefaultService.getCourseDetails([courseCode])
      setCourseDetails((prev) => { return { ...prev, [response[0].code]: response[0] } })
      setPlan((prev) => {
        if (prev == null) return prev
        const newClasses = [...prev.validatable_plan.classes]
        newClasses[semIdx] = [...prev.validatable_plan.classes[semIdx]]
        newClasses[semIdx].push({
          is_concrete: true,
          code: response[0].code
        })
        return { ...prev, validatable_plan: { ...prev.validatable_plan, classes: newClasses } }
      })
    } catch (err) {
      handleErrors(err)
    }
  }

  useEffect(() => {
    if (params?.plannerId != null) {
      getPlanById(params.plannerId).catch(err => {
        handleErrors(err)
      })
    } else {
      getDefaultPlan().catch(err => {
        handleErrors(err)
      })
    }
  }, [])

  useEffect(() => {
    if ((status === 'validating' || status === 'ready') && plan !== null) {
      // dont validate if the classes are rearranging the same semester at previous validation
      let changed = plan.validatable_plan.classes.length !== previousClasses.current.length
      if (!changed) {
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
        setStatus('validating')
        validate(plan.validatable_plan).catch(err => {
          setValidationResult({
            diagnostics: [{
              is_warning: false,
              message: `Error interno: ${String(err)}`
            }],
            course_superblocks: {}
          })
        })
      }
      setStatus('ready')
    }
  }, [status, plan])

  async function openModal (equivalence: Equivalence | EquivalenceId, semester: number, index: number): Promise<void> {
    if ('courses' in equivalence) {
      setModalData({ equivalence, semester, index })
    } else {
      const response = await DefaultService.getEquivalenceDetails([equivalence.code])
      setModalData({ equivalence: response[0], semester, index })
    }
    setIsModalOpen(true)
  }

  async function closeModal (selection?: string): Promise<void> {
    if (selection != null && modalData !== undefined && plan != null) {
      const pastClass = plan.validatable_plan.classes[modalData.semester][modalData.index]
      if (selection === pastClass.code) { setIsModalOpen(false); return }
      for (const existingCourse of plan?.validatable_plan.classes.flat()) {
        if (existingCourse.code === selection) {
          alert(`${selection} ya se encuentra en el plan, seleccione otro curso por favor`)
          return
        }
      }
      setStatus('validating')
      const details = (await DefaultService.getCourseDetails([selection]))[0]
      setCourseDetails((prev) => { return { ...prev, [details.code]: details } })
      setPlan((prev) => {
        if (prev == null) return prev
        const newClasses = [...prev.validatable_plan.classes]
        newClasses[modalData.semester] = [...prev.validatable_plan.classes[modalData.semester]]
        const oldEquivalence = 'credits' in pastClass ? pastClass : pastClass.equivalence
        newClasses[modalData.semester][modalData.index] = {
          is_concrete: true,
          code: selection,
          equivalence: oldEquivalence
        }
        if (oldEquivalence !== undefined && oldEquivalence.credits !== details.credits) {
          if (oldEquivalence.credits > details.credits) {
            newClasses[modalData.semester].splice(modalData.index, 1,
              {
                is_concrete: true,
                code: selection,
                equivalence: {
                  ...oldEquivalence,
                  credits: details.credits
                }
              },
              {
                is_concrete: false,
                code: oldEquivalence.code,
                credits: oldEquivalence.credits - details.credits
              }
            )
          } else {
            // To-DO: handle when credis exced necesary
            // General logic: if there are not other courses with the same code then it dosnt matters
            // If there are other course with the same code, and exact same credits that this card exceed, delete the other

            // On other way, one should decresed credits of other course with the same code
            // Problem In this part: if i exceed by 5 and have a course of 4 and 10, what do i do
            // option 1: delete the course with 4 and decresed the one of 10 by 1
            // option 2: decresed the one of 10 to 5

            // Partial solution: just consume anything we find
            const semester = newClasses[modalData.semester]
            let extra = details.credits - oldEquivalence.credits
            for (let i = semester.length; i-- > 0;) {
              const equiv = semester[i]
              if ('credits' in equiv && equiv.code === oldEquivalence.code) {
                if (equiv.credits <= extra) {
                  // Consume this equivalence entirely
                  semester.splice(modalData.index, 1)
                  extra -= equiv.credits
                } else {
                  // Consume part of this equivalence
                  equiv.credits -= extra
                  extra = 0
                }
              }
            }

            // Increase the credits of the equivalence
            // We might not have found all the missing credits, but that's ok
            newClasses[modalData.semester].splice(modalData.index, 1,
              {
                is_concrete: true,
                code: selection,
                equivalence: {
                  ...oldEquivalence,
                  credits: details.credits
                }
              }
            )
          }
        }
        return { ...prev, validatable_plan: { ...prev.validatable_plan, classes: newClasses } }
      })
    }
    setIsModalOpen(false)
  }

  return (
    <div className={`w-full h-full p-3 flex flex-grow overflow-hidden flex-row ${status === 'validating' ? 'cursor-wait' : ''}`}>
      <CourseSelectorDialog equivalence={modalData?.equivalence} open={isModalOpen} onClose={async (selection?: string) => await closeModal(selection)}/>
      {(status !== 'loading' && error === null) && <>
        <div className={'flex flex-col w-5/6 flex-grow'}>
          <ul className={'w-full mb-3 mt-2 relative'}>
            <li className={'inline text-md ml-3 mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Major:</div> Ingeniería y Ciencias Ambientales</li>
            <li className={'inline text-md mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Minor:</div> Por seleccionar</li>
            <li className={'inline text-md mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Titulo:</div> Por seleccionar</li>
            {plan != null && 'id' in plan && <li className={'inline text-md ml-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Plan:</div> {plan.name}</li>}
          </ul>
          <ControlTopBar
            reset={getDefaultPlan}
            save={savePlan}
            validating={status === 'validating'}
          />
          <PlanBoard
            plan={plan?.validatable_plan ?? null}
            courseDetails={courseDetails}
            setPlan={setPlan}
            openModal={openModal}
            addCourse={addCourse}
            validating={status === 'validating'}
            validationResult={validationResult}
          />
        </div>
        <ErrorTray diagnostics={validationResult?.diagnostics ?? []} validating={status === 'validating'}/>
        </>}

        {status === 'loading' && error === null && <Spinner message='Cargando planificación...' />}
        {error !== null && <div className={'w-full h-full flex flex-col justify-center items-center'}>
          <p className={'text-2xl font-semibold mb-4'}>Error al cargar plan</p>
          <p className={'text-sm font-normal'}>{error}</p>
        </div>}
    </div>
  )
}

export default Planner
