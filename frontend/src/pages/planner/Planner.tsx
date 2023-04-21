import { Spinner } from '../../components/Spinner'
import ErrorTray from './ErrorTray'
import PlanBoard from './planBoard/PlanBoard'
import ControlTopBar from './ControlTopBar'
import MyDialog from '../../components/Dialog'
import { useParams } from '@tanstack/react-router'
import { useState, useEffect, useRef } from 'react'
import { Listbox } from '@headlessui/react'
import { Major, Minor, Title, DefaultService, ValidatablePlan, Course, Equivalence, ConcreteId, EquivalenceId, FlatValidationResult, PlanView } from '../../client'

export type PseudoCourseId = ConcreteId | EquivalenceId
export type PseudoCourseDetail = Course | Equivalence

type ModalData = { equivalence: Equivalence, semester: number, index: number } | undefined

interface CurriculumData {
  majors: { [code: string]: Major }
  minors: { [code: string]: Minor }
  titles: { [code: string]: Title }
}
enum PlannerStatus {
  LOADING = 'LOADING',
  VALIDATING = 'VALIDATING',
  SAVING = 'SAVING',
  ERROR = 'ERROR',
  READY = 'READY',
}
/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */
const Planner = (): JSX.Element => {
  const [planName, setPlanName] = useState<string>('')
  const [validatablePlan, setValidatablePlan] = useState<ValidatablePlan | null>(null)
  const [courseDetails, setCourseDetails] = useState<{ [code: string]: Course | Equivalence }>({})
  const [curriculumData, setCurriculumData] = useState<CurriculumData | null>(null)
  const [modalData, setModalData] = useState<ModalData>()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [plannerStatus, setPlannerStatus] = useState<PlannerStatus>(PlannerStatus.LOADING)
  const [validationResult, setValidationResult] = useState<FlatValidationResult | null>(null)
  const [error, setError] = useState<String | null>(null)

  const previousClasses = useRef<PseudoCourseId[][]>([[]])

  const params = useParams()

  async function getDefaultPlan (ValidatablePlan?: ValidatablePlan): Promise<void> {
    console.log('getting Basic Plan...')
    // TODO: Use current user to generate plan if logged in
    if (ValidatablePlan === undefined) {
      ValidatablePlan = await DefaultService.emptyGuestPlan()
    }
    const response: ValidatablePlan = await DefaultService.generatePlan(ValidatablePlan)
    await getCourseDetails(response.classes.flat()).catch(err => {
      setValidationResult({
        diagnostics: [{
          is_warning: false,
          message: `Error interno: ${String(err)}`
        }],
        course_superblocks: {}
      })
    })
    setCurriculumData(await loadCurriculumsData(response.curriculum.cyear, response.curriculum.major))
    setValidatablePlan(response)
    await validate(response).catch(err => {
      setValidationResult({
        diagnostics: [{
          is_warning: false,
          message: `Error interno: ${String(err)}`
        }],
        course_superblocks: {}
      })
    })
    console.log('data loaded')
  }

  async function getPlanById (id: string): Promise<void> {
    console.log('getting Plan by Id...')
    try {
      const response: PlanView = await DefaultService.readPlan(id)
      setCurriculumData(await loadCurriculumsData(response.validatable_plan.curriculum.cyear, response.validatable_plan.curriculum.major))
      setValidatablePlan(response.validatable_plan)
      setPlanName(response.name)
      await getCourseDetails(response.validatable_plan.classes.flat()).catch(err => {
        setValidationResult({
          diagnostics: [{
            is_warning: false,
            message: `Error interno: ${String(err)}`
          }],
          course_superblocks: {}
        })
      })
      await validate(response.validatable_plan).catch(err => {
        setValidationResult({
          diagnostics: [{
            is_warning: false,
            message: `Error interno: ${String(err)}`
          }],
          course_superblocks: {}
        })
      })
    } catch (err) {
      alert(err)
      window.location.href = '/planner'
    }
    console.log('data loaded')
  }

  async function getCourseDetails (courses: PseudoCourseId[]): Promise<void> {
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
    const dict = [...responseCourseDetails, ...responseEquivalenceDetails].reduce((acc: { [code: string]: PseudoCourseDetail }, curr: PseudoCourseDetail) => {
      acc[curr.code] = curr
      return acc
    }, {})
    setCourseDetails((prev) => { return { ...prev, ...dict } })
  }

  async function validate (validatablePlan: ValidatablePlan): Promise<void> {
    const response = await DefaultService.validatePlan(validatablePlan)
    setValidationResult(response)
    setPlannerStatus(PlannerStatus.READY)
    // Es necesario hacer una copia profunda del plan para comparar, pues si se copia el objeto entero
    // entonces la copia es modificada junto al objeto original. Lo ideal seria usar una librearia para esto en el futuro
    previousClasses.current = JSON.parse(JSON.stringify(validatablePlan.classes))
  }

  async function savePlan (): Promise<void> {
    if (validatablePlan == null) {
      alert('No se ha generado un plan aun')
      return
    }
    if (params?.plannerId != null) {
      setPlannerStatus(PlannerStatus.VALIDATING)
      try {
        await DefaultService.updatePlan(params.plannerId, validatablePlan)
        alert('Plan actualizado exitosamente.')
      } catch (err) {
        alert(err)
      }
      setPlannerStatus(PlannerStatus.READY)
    } else {
      const planName = prompt('¿Cómo quieres llamarle a esta planificación?')
      if (planName == null || planName === '') return
      setPlannerStatus(PlannerStatus.VALIDATING)
      try {
        const res = await DefaultService.savePlan(planName, validatablePlan)
        alert('Plan guardado exitosamente.')
        window.location.href = `/planner/${res.id}`
      } catch (err) {
        alert(err)
      }
    }
    setPlannerStatus(PlannerStatus.READY)
  }

  async function addCourse (semIdx: number): Promise<void> {
    if (validatablePlan == null) {
      return
    }
    const courseCodeRaw = prompt('Sigla del curso?')
    if (courseCodeRaw == null || courseCodeRaw === '') return
    const courseCode = courseCodeRaw.toUpperCase()
    for (const existingCourse of validatablePlan?.classes.flat()) {
      if (existingCourse.code === courseCode) {
        alert(`${courseCode} ya se encuentra en el plan, seleccione otro curso por favor`)
        return
      }
    }
    setPlannerStatus(PlannerStatus.VALIDATING)
    try {
      const response = await DefaultService.getCourseDetails([courseCode])
      setCourseDetails((prev) => { return { ...prev, [response[0].code]: response[0] } })
      setValidatablePlan((prev) => {
        if (prev == null) return prev
        const newClasses = [...prev.classes]
        newClasses[semIdx] = [...prev.classes[semIdx]]
        newClasses[semIdx].push({
          is_concrete: true,
          code: response[0].code
        })
        return { ...prev, classes: newClasses }
      })
    } catch (err) {
      alert(err)
    }
  }

  async function loadCurriculumsData (cYear: string, cMajor?: string): Promise<CurriculumData> {
    const [majors, minors, titles] = await Promise.all([
      DefaultService.getMajors(cYear),
      DefaultService.getMinors(cYear, cMajor),
      DefaultService.getTitles(cYear)
    ])
    const curriculumData: CurriculumData = {
      majors: majors.reduce((dict: { [code: string]: Major }, m: Major) => {
        dict[m.code] = m
        return dict
      }, {}),
      minors: minors.reduce((dict: { [code: string]: Minor }, m: Minor) => {
        dict[m.code] = m
        return dict
      }, {}),
      titles: titles.reduce((dict: { [code: string]: Title }, t: Title) => {
        dict[t.code] = t
        return dict
      }, {})
    }
    return curriculumData
  }

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
    if (selection != null && modalData !== undefined && validatablePlan != null) {
      const pastClass = validatablePlan.classes[modalData.semester][modalData.index]
      if (selection === pastClass.code) { setIsModalOpen(false); return }
      for (const existingCourse of validatablePlan.classes.flat()) {
        if (existingCourse.code === selection) {
          alert(`${selection} ya se encuentra en el plan, seleccione otro curso por favor`)
          return
        }
      }
      setPlannerStatus(PlannerStatus.VALIDATING)
      const response = await DefaultService.getCourseDetails([selection])
      setCourseDetails((prev) => { return { ...prev, [response[0].code]: response[0] } })
      setValidatablePlan((prev) => {
        if (prev == null) return prev
        const newClasses = [...prev.classes]
        newClasses[modalData.semester] = [...prev.classes[modalData.semester]]
        let newEquivalence: EquivalenceId | undefined
        if ('credits' in pastClass) {
          newEquivalence = pastClass
        } else newEquivalence = pastClass.equivalence
        newClasses[modalData.semester][modalData.index] = {
          is_concrete: true,
          code: selection,
          equivalence: newEquivalence
        }
        if (newEquivalence !== undefined && newEquivalence.credits !== response[0].credits) {
          if (newEquivalence.credits > response[0].credits) {
            newClasses[modalData.semester].splice(modalData.index + 1, 0,
              {
                is_concrete: false,
                code: newEquivalence.code,
                credits: newEquivalence.credits - response[0].credits
              }
            )
          } else {
            // To-DO: handle when credis exced necesary
            // General logic: if there are not other courses with the same code then it dosnt matters
            // If there are other course with the same code, and exact same creddits that this card exceed, delete the other

            // On other way, one should decresed credits of other course with the same code
            // Problem In this part: if i exceed by 5 and have a course of 4 and 10, what do i do
            // option 1: delete the course with 4 and decresed the one of 10 by 1
            // option 2: decresed the one of 10 to 5
            console.log('help')
          }
        }
        return { ...prev, classes: newClasses }
      })
    }
    setIsModalOpen(false)
  }

  function selectMajor (major: Major): void {
    setPlannerStatus(PlannerStatus.VALIDATING)
    setValidatablePlan((prev) => {
      if (prev == null) return prev
      const newCurriculum = prev.curriculum
      newCurriculum.major = major.code
      return { ...prev, curriculum: newCurriculum }
    })
  }

  function selectMinor (minor: Minor): void {
    setPlannerStatus(PlannerStatus.VALIDATING)
    setValidatablePlan((prev) => {
      if (prev == null) return prev
      const newCurriculum = prev.curriculum
      newCurriculum.minor = minor.code
      return { ...prev, curriculum: newCurriculum }
    })
  }

  function selectTitle (title: Title): void {
    setPlannerStatus(PlannerStatus.VALIDATING)
    setValidatablePlan((prev) => {
      if (prev == null) return prev
      const newCurriculum = prev.curriculum
      newCurriculum.title = title.code
      return { ...prev, curriculum: newCurriculum }
    })
  }

  useEffect(() => {
    async function fetchData (): Promise<void> {
      setPlannerStatus(PlannerStatus.LOADING)
      try {
        if (params?.plannerId != null) {
          await getPlanById(params.plannerId)
        } else {
          await getDefaultPlan()
        }
      } catch (error) {
        setError('Hubo un error al cargar el planner')
        console.error(error)
        setPlannerStatus(PlannerStatus.ERROR)
      }
    }
    void fetchData()
  }, [])

  useEffect(() => {
    if (plannerStatus !== 'LOADING' && validatablePlan != null) {
      // dont validate if the classes are rearranging the same semester at previous validation
      let classesChanged = validatablePlan.classes.length !== previousClasses.current.length
      if (!classesChanged) {
        for (let idx = 0; idx < validatablePlan.classes.length; idx++) {
          const cur = [...validatablePlan.classes[idx]].sort((a, b) => a.code.localeCompare(b.code))
          const prev = [...previousClasses.current[idx]].sort((a, b) => a.code.localeCompare(b.code))
          if (JSON.stringify(cur) !== JSON.stringify(prev)) {
            classesChanged = true
            break
          }
        }
      }
      if (classesChanged) {
        validate(validatablePlan).catch(err => {
          setValidationResult({
            diagnostics: [{
              is_warning: false,
              message: `Error interno: ${String(err)}`
            }],
            course_superblocks: {}
          })
        })
      }
    }
  }, [plannerStatus, validatablePlan])

  return (
    <div className={`w-full h-full p-3 flex flex-grow overflow-hidden flex-row ${(plannerStatus !== 'ERROR' && plannerStatus !== 'READY') ? 'cursor-wait' : ''}`}>
      <MyDialog equivalence={modalData?.equivalence} open={isModalOpen} onClose={async (selection?: string) => await closeModal(selection)}/>
      {plannerStatus === 'LOADING' && (
        <Spinner message='Cargando planificación...' />
      )}

      {plannerStatus === 'ERROR' && (<div className={'w-full h-full flex flex-col justify-center items-center'}>
        <p className={'text-2xl font-semibold mb-4'}>Error al cargar plan</p>
        <p className={'text-sm font-normal'}>{error}</p>
      </div>)}

      {plannerStatus !== 'LOADING' && plannerStatus !== 'ERROR' && <>
        <div className={'flex flex-col w-5/6 flex-grow'}>
          {curriculumData !== null && validatablePlan !== null &&
            <ul className={'w-full mb-3 mt-2 relative'}>
              <li className={'inline text-md ml-3 mr-5 font-semibold'}>
                <div className={'text-sm inline mr-1 font-normal'}>Major:</div>
                <Listbox value={curriculumData.majors[validatablePlan.curriculum.major ?? '']} onChange={selectMajor}>
                  <Listbox.Button>{curriculumData.majors[validatablePlan.curriculum.major ?? ''].name}</Listbox.Button>
                  <Listbox.Options>
                    {Object.keys(curriculumData.majors).map((key) => {
                      return (
                        <Listbox.Option
                          key={key}
                          value={curriculumData.majors[key]}
                        >
                          {curriculumData.majors[key].name}
                        </Listbox.Option>
                      )
                    })}
                  </Listbox.Options>
                </Listbox>
              </li>
              <li className={'inline text-md mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Minor:</div>
                <Listbox value={curriculumData.minors[validatablePlan.curriculum.minor ?? '']} onChange={selectMinor}>
                  <Listbox.Button>{curriculumData.minors[validatablePlan.curriculum.minor ?? ''].name}</Listbox.Button>
                  <Listbox.Options>
                    {Object.keys(curriculumData.minors).map((key) => {
                      return (
                        <Listbox.Option
                          key={key}
                          value={curriculumData.minors[key]}
                        >
                          {curriculumData.minors[key].name}
                        </Listbox.Option>
                      )
                    })}
                  </Listbox.Options>
                </Listbox>
              </li>
              <li className={'inline text-md mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Titulo:</div>
                <Listbox value={curriculumData.titles[validatablePlan.curriculum.title ?? '']} onChange={selectTitle}>
                  <Listbox.Button>{curriculumData.titles[validatablePlan.curriculum.title ?? ''].name}</Listbox.Button>
                  <Listbox.Options>
                    {Object.keys(curriculumData.titles).map((key) => {
                      return (
                        <Listbox.Option
                          key={key}
                          value={curriculumData.titles[key]}
                        >
                          {curriculumData.titles[key].name}
                        </Listbox.Option>
                      )
                    })}
                  </Listbox.Options>
                </Listbox>
              </li>
              {planName !== '' && <li className={'inline text-md ml-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Plan:</div> {planName}</li>}
            </ul>
          }
          <ControlTopBar
            reset={getDefaultPlan}
            save={savePlan}
            validating={plannerStatus !== 'READY'}
          />
          <PlanBoard
            classesGrid={validatablePlan?.classes ?? []}
            classesDetails={courseDetails}
            setPlan={setValidatablePlan}
            openModal={openModal}
            addCourse={addCourse}
            validating={plannerStatus !== 'READY'}
            validationResult={validationResult}
          />
        </div>
        <ErrorTray diagnostics={validationResult?.diagnostics ?? []} validating={plannerStatus === 'VALIDATING'}/>
        </>}
    </div>
  )
}

export default Planner
