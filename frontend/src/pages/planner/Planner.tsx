import ErrorTray from './ErrorTray'
import PlanBoard from './planBoard/PlanBoard'
import ControlTopBar from './ControlTopBar'
import MyDialog from '../../components/Modal'
import { useParams } from '@tanstack/react-router'
import { useState, useEffect, useRef } from 'react'
import { DefaultService, ValidatablePlan, Course, Equivalence, ConcreteId, EquivalenceId, FlatValidationResult, PlanView } from '../../client'

type PseudoCourse = ConcreteId | EquivalenceId

type ModalData = { equivalence: Equivalence, semester: number, index: number } | undefined
interface EmptyPlan {
  validatable_plan: ValidatablePlan
}

/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */
const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<PlanView | EmptyPlan>({ validatable_plan: { classes: [], next_semester: 0 } })
  const [courseDetails, setCourseDetails] = useState<{ [code: string]: Course | Equivalence }>({})
  const [modalData, setModalData] = useState<ModalData>()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const previousClasses = useRef<PseudoCourse[][]>([[]])
  const [loading, setLoading] = useState(true)
  const [validating, setValidanting] = useState(false)
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
    setValidanting(true)
    console.log('getting Courses Details...')
    const coursesCodes = []
    const equivalenceCodes = []
    for (const courseid of courses) {
      if (courseid.is_concrete === true) { coursesCodes.push(courseid.code) } else { equivalenceCodes.push(courseid.code) }
    }
    let responseEquivalenceDetails: Equivalence[] = []
    let responseCourseDetails: Course[] = []
    if (coursesCodes.length > 0) responseCourseDetails = await DefaultService.getCourseDetails(coursesCodes)
    if (equivalenceCodes.length > 0) responseEquivalenceDetails = await DefaultService.getEquivalenceDetails(equivalenceCodes)
    // transform response to dict with key code:
    const dict = [...responseCourseDetails, ...responseEquivalenceDetails].reduce((acc: { [code: string]: Course | Equivalence }, curr: Course | Equivalence) => {
      acc[curr.code] = curr
      return acc
    }, {})
    setCourseDetails((prev) => { return { ...prev, ...dict } })
    console.log('Details loaded')
    setValidanting(false)
  }

  async function validate (validatablePlan: ValidatablePlan): Promise<void> {
    setValidanting(true)
    console.log('validating...')
    const response = await DefaultService.validatePlan(validatablePlan)
    setValidationResult(response)
    console.log('validated')
    setValidanting(false)
    // Es necesario hacer una copia profunda del plan para comparar, pues si se copia el objeto entero
    // entonces la copia es modificada junto al objeto original. Lo ideal seria usar una librearia para esto en el futuro
    previousClasses.current = JSON.parse(JSON.stringify(validatablePlan.classes))
  }

  async function savePlan (): Promise<void> {
    if (params?.plannerId != null) {
      setValidanting(true)
      try {
        await DefaultService.updatePlan(params.plannerId, plan.validatable_plan)
        alert('Plan actualizado exitosamente')
      } catch (err) {
        alert(err)
      }
    } else {
      const planName = prompt('Nombre de la malla?')
      if (planName == null || planName === '') return
      setValidanting(true)
      try {
        const res = await DefaultService.savePlan(planName, plan.validatable_plan)
        alert('Plan guardado exitosamente')
        window.location.href = `/planner/${res.id}`
      } catch (err) {
        alert(err)
      }
    }
    setValidanting(false)
  }

  async function addCourse (semIdx: number): Promise<void> {
    const courseCodeRaw = prompt('Course code?')
    if (courseCodeRaw == null || courseCodeRaw === '') return
    const courseCode = courseCodeRaw.toUpperCase()
    for (const existingCourse of plan?.validatable_plan.classes.flat()) {
      if (existingCourse.code === courseCode) {
        alert(`${courseCode} ya se encuentra en el plan, seleccione otro curso por favor`)
        return
      }
    }
    setValidanting(true)
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
        return { ...prev, validatable_plan: { ...prev.validatable_plan, classes: newClasses } }
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
    if (selection != null && modalData !== undefined) {
      const pastClass = plan.validatable_plan.classes[modalData.semester][modalData.index]
      if (selection === pastClass.code) { setIsModalOpen(false); return }
      for (const existingCourse of plan?.validatable_plan.classes.flat()) {
        if (existingCourse.code === selection) {
          alert(`${selection} ya se encuentra en el plan, seleccione otro curso por favor`)
          return
        }
      }

      setValidanting(true)
      const response = await DefaultService.getCourseDetails([selection])
      setCourseDetails((prev) => { return { ...prev, [response[0].code]: response[0] } })
      setPlan((prev) => {
        const newClasses = [...prev.validatable_plan.classes]
        newClasses[modalData.semester] = [...prev.validatable_plan.classes[modalData.semester]]
        let newEquivalence: EquivalenceId | undefined
        if ('credits' in pastClass) {
          newEquivalence = pastClass
        } else newEquivalence = pastClass.equivalence
        newClasses[modalData.semester][modalData.index] = {
          is_concrete: true,
          code: selection,
          equivalence: newEquivalence
        }
        return { ...prev, validatable_plan: { ...prev.validatable_plan, classes: newClasses } }
      })
    }
    setIsModalOpen(false)
  }

  return (
    <div className={`w-full h-full pb-10 flex flex-row ${validating ? 'cursor-wait' : ''}`}>
      <MyDialog equivalence={modalData?.equivalence} open={isModalOpen} onClose={async (selection?: string) => await closeModal(selection)}/>
      {(!loading)
        ? <>
        <div className={'flex flex-col w-5/6'}>
          <ul className={'w-full mb-1 mt-2 relative'}>
            <li className={'inline text-md ml-3 mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Major:</div> Ingeniería y Ciencias Ambientales</li>
            <li className={'inline text-md mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Minor:</div> Por seleccionar</li>
            <li className={'inline text-md mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Titulo:</div> Por seleccionar</li>
            {'id' in plan && <li className={'inline text-md ml-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Plan:</div> {plan.name}</li>}
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
            openModal={openModal}
            addCourse={addCourse}
            validating={validating}
            validationResult={validationResult}
          />
        </div>
        <ErrorTray diagnostics={validationResult?.diagnostics ?? []} validating={validating}/>
        </>
        : <div>Loading</div>}
    </div>
  )
}

export default Planner
