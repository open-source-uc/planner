import { Spinner } from '../../components/Spinner'
import ErrorTray from './ErrorTray'
import PlanBoard from './planBoard/PlanBoard'
import ControlTopBar from './ControlTopBar'
import CourseSelectorDialog from './CourseSelectorDialog'
import AlertModal from '../../components/AlertModal'
import { useParams } from '@tanstack/react-router'
import { Fragment, useState, useEffect, useRef } from 'react'
import { Listbox, Transition } from '@headlessui/react'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import { ApiError, Major, Minor, Title, DefaultService, ValidatablePlan, Course, Equivalence, ConcreteId, EquivalenceId, FlatValidationResult, PlanView } from '../../client'
import { useAuth } from '../../contexts/auth.context'
import { toast } from 'react-toastify'
import down_arrow from '../../assets/down_arrow.svg'
import 'react-toastify/dist/ReactToastify.css'
import DebugGraph from '../../components/DebugGraph'

export type PseudoCourseId = ConcreteId | EquivalenceId
export type PseudoCourseDetail = Course | Equivalence

type ModalData = { equivalence: Equivalence | undefined, selector: boolean, semester: number, index: number } | undefined

interface CurriculumData {
  majors: { [code: string]: Major }
  minors: { [code: string]: Minor }
  titles: { [code: string]: Title }
}

interface CurriculumSelectorProps {
  planName: String
  curriculumData: CurriculumData
  validatablePlan: ValidatablePlan
  selectMajor: Function
  selectMinor: Function
  selectTitle: Function
}

enum PlannerStatus {
  LOADING = 'LOADING',
  VALIDATING = 'VALIDATING',
  SAVING = 'SAVING',
  ERROR = 'ERROR',
  READY = 'READY',
}

const findCourseSuperblock = (validationResults: FlatValidationResult | null, semester: number, index: number): string | null => {
  if (validationResults == null) return null
  const rawSuperblock = validationResults.course_superblocks[semester][index]
  return rawSuperblock.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(' ', '').split(' ')[0]
}

const isApiError = (err: any): err is ApiError => {
  return err.status !== undefined
}

/**
 * The selector of major, minor and tittle.
 */
const CurriculumSelector = ({
  planName,
  curriculumData,
  validatablePlan,
  selectMajor,
  selectMinor,
  selectTitle
}: CurriculumSelectorProps): JSX.Element => {
  return (
    <ul className={'curriculumSelector'}>
      <li className={'selectorElement'}>
        <div className={'selectorName'}>Major:</div>
        <Listbox value={validatablePlan.curriculum.major !== undefined && validatablePlan.curriculum.major !== null ? curriculumData.majors[validatablePlan.curriculum.major] : {}} onChange={(m) => selectMajor(m)}>
          <Listbox.Button className={'selectorButton'}>
            <span className="inline truncate">{validatablePlan.curriculum.major !== undefined && validatablePlan.curriculum.major !== null ? curriculumData.majors[validatablePlan.curriculum.major].name : 'Por elegir'}</span>
            <img className="inline" src={down_arrow} alt="Seleccionar Major" />
          </Listbox.Button>
          <Transition
            as={Fragment}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Listbox.Options className={'curriculumOptions'} style={{ zIndex: 1 }}>
              {Object.keys(curriculumData.majors).map((key) => (
                <Listbox.Option
                  className={({ active }) =>
                  `curriculumOption ${
                    active ? 'bg-place-holder text-amber-800' : 'text-gray-900'
                  }`
                  }key={key}
                  value={curriculumData.majors[key]}
                >
                  {({ selected }) => (
                    <>
                      <span
                        className={`block truncate ${
                          selected ? 'font-medium text-black' : 'font-normal'
                        }`}
                      >
                        {curriculumData.majors[key].name}
                      </span>
                      {selected
                        ? (
                        <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-800">
                          *
                        </span>
                          )
                        : null}
                    </>
                  )}
                </Listbox.Option>
              ))}
            </Listbox.Options>
          </Transition>
        </Listbox>
      </li>
      <li className={'selectorElement'}>
        <div className={'selectorName'}>Minor:</div>
        <Listbox
          value={validatablePlan.curriculum.minor !== undefined && validatablePlan.curriculum.minor !== null ? curriculumData.minors[validatablePlan.curriculum.minor] : {}}
          onChange={(m) => selectMinor(m)}>
          <Listbox.Button className={'selectorButton'}>
            <span className="inline truncate">{validatablePlan.curriculum.minor !== undefined && validatablePlan.curriculum.minor !== null ? curriculumData.minors[validatablePlan.curriculum.minor].name : 'Por elegir'}</span>
            <img className="inline" src={down_arrow} alt="Seleccionar Minor" />
          </Listbox.Button>
          <Transition
            as={Fragment}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Listbox.Options className={'curriculumOptions'} style={{ zIndex: 1 }}>
              {Object.keys(curriculumData.minors).map((key) => (
                <Listbox.Option
                  className={({ active }) =>
                    `curriculumOption ${
                      active ? 'bg-place-holder text-amber-800' : 'text-gray-900'
                    }`
                  }key={key}
                  value={curriculumData.minors[key]}
                >
                  {({ selected }) => (
                    <>
                      <span
                        className={`block truncate ${
                          selected ? 'font-medium text-black' : 'font-normal'
                        }`}
                      >
                        {curriculumData.minors[key].name}
                      </span>
                      {selected
                        ? (
                        <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-800">
                          *
                        </span>
                          )
                        : null}
                    </>
                  )}
                </Listbox.Option>
              ))}
            </Listbox.Options>
          </Transition>
        </Listbox>
      </li>
      <li className={'selectorElement'}>
        <div className={'selectorName'}>Titulo:</div>
        <Listbox value={validatablePlan.curriculum.title !== undefined && validatablePlan.curriculum.title !== null ? curriculumData.titles[validatablePlan.curriculum.title] : {}} onChange={(t) => selectTitle(t)}>
          <Listbox.Button className="selectorButton">
            <span className="inline truncate">{validatablePlan.curriculum.title !== undefined && validatablePlan.curriculum.title !== null ? curriculumData.titles[validatablePlan.curriculum.title].name : 'Por elegir'}</span>
            <img className="inline" src={down_arrow} alt="Seleccionar Titulo" />
          </Listbox.Button>
          <Transition
            as={Fragment}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Listbox.Options className={'curriculumOptions'} style={{ zIndex: 1 }}>
              {Object.keys(curriculumData.titles).map((key) => (
                <Listbox.Option
                  className={({ active }) =>
                  `curriculumOption ${
                    active ? 'bg-place-holder text-amber-800' : ''
                  }`
                  }key={key}
                  value={curriculumData.titles[key]}
                >
                  {({ selected }) => (
                    <>
                      <span
                        className={`block truncate ${
                          selected ? 'font-medium text-black' : 'font-normal'
                        }`}
                      >
                        {curriculumData.titles[key].name}
                      </span>
                      {selected
                        ? (
                        <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-800">
                          *
                        </span>
                          )
                        : null}
                    </>
                  )}
                </Listbox.Option>
              ))}
            </Listbox.Options>
          </Transition>
        </Listbox>
      </li>
      {planName !== '' && <li className={'inline text-md ml-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Plan:</div> {planName}</li>}
    </ul>
  )
}

/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */
const Planner = (): JSX.Element => {
  const [planName, setPlanName] = useState<string>('')
  const [validatablePlan, setValidatablePlan] = useState<ValidatablePlan | null >(null)
  const [courseDetails, setCourseDetails] = useState<{ [code: string]: Course | Equivalence }>({})
  const [curriculumData, setCurriculumData] = useState<CurriculumData | null>(null)
  const [modalData, setModalData] = useState<ModalData>()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [plannerStatus, setPlannerStatus] = useState<PlannerStatus>(PlannerStatus.LOADING)
  const [validationResult, setValidationResult] = useState<FlatValidationResult | null>(null)
  const [error, setError] = useState<String | null>(null)
  const [popUpAlert, setPopUpAlert] = useState<{ title: string, major: string, desc: string, isOpen: boolean }>({ title: '', major: '', desc: '', isOpen: false })

  const previousCurriculum = useRef<{ major: String | undefined, minor: String | undefined, title: String | undefined }>({ major: '', minor: '', title: '' })
  const previousClasses = useRef<PseudoCourseId[][]>([[]])

  const params = useParams()
  const authState = useAuth()

  function handleErrors (err: unknown): void {
    console.log(err)
    setPlannerStatus(PlannerStatus.ERROR)
    if (isApiError(err)) {
      switch (err.status) {
        case 401:
          console.log('token invalid or expired, loading re-login page')
          toast.error('Token invalido. Redireccionando a pagina de inicio...', {
            toastId: 'ERROR401'
          })
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

  async function getDefaultPlan (ValidatablePlan?: ValidatablePlan): Promise<void> {
    try {
      console.log('getting Basic Plan...')
      if (ValidatablePlan === undefined) {
        ValidatablePlan = authState?.user == null ? await DefaultService.emptyGuestPlan() : await DefaultService.emptyPlanForUser()
      }
      // truncate the validatablePlan to the last not empty semester
      while (ValidatablePlan.classes.length > 0 && ValidatablePlan.classes[ValidatablePlan.classes.length - 1].length === 0) {
        ValidatablePlan.classes.pop()
      }
      const response: ValidatablePlan = await DefaultService.generatePlan(ValidatablePlan)
      await Promise.all([
        getCourseDetails(response.classes.flat()),
        loadCurriculumsData(response.curriculum.cyear.raw, response.curriculum.major),
        validate(response)
      ])
      setValidatablePlan(response)
      console.log('data loaded')
    } catch (err) {
      handleErrors(err)
    }
  }

  async function getPlanById (id: string): Promise<void> {
    try {
      console.log('getting Plan by Id...')
      const response: PlanView = await DefaultService.readPlan(id)
      await Promise.all([
        getCourseDetails(response.validatable_plan.classes.flat()),
        loadCurriculumsData(response.validatable_plan.curriculum.cyear.raw, response.validatable_plan.curriculum.major),
        validate(response.validatable_plan)
      ])
      setValidatablePlan(response.validatable_plan)
      setPlanName(response.name)
      console.log('data loaded')
    } catch (err) {
      handleErrors(err)
    }
  }

  async function fetchData (): Promise<void> {
    try {
      if (params?.plannerId != null) {
        if (validatablePlan !== null) {
          await getDefaultPlan(validatablePlan)
        } else {
          await getPlanById(params.plannerId)
        }
      } else {
        await getDefaultPlan(validatablePlan ?? undefined)
      }
    } catch (error) {
      setError('Hubo un error al cargar el planner')
      console.error(error)
      setPlannerStatus(PlannerStatus.ERROR)
    }
  }

  async function getCourseDetails (courses: PseudoCourseId[]): Promise<void> {
    console.log('getting Courses Details...')
    const coursesCodes = new Set<string>()
    const equivalenceCodes = new Set<string>()
    for (const courseid of courses) {
      if (courseid.is_concrete === true) { coursesCodes.add(courseid.code) } else { equivalenceCodes.add(courseid.code) }
    }
    try {
      const promises = []
      if (coursesCodes.size > 0) promises.push(DefaultService.getCourseDetails(Array.from(coursesCodes)))
      if (equivalenceCodes.size > 0) promises.push(DefaultService.getEquivalenceDetails(Array.from(equivalenceCodes)))
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
      previousCurriculum.current = {
        major: validatablePlan.curriculum.major,
        minor: validatablePlan.curriculum.minor,
        title: validatablePlan.curriculum.title
      }
      setValidationResult(response)
      setPlannerStatus(PlannerStatus.READY)
      // No deberia ser necesario hacer una copia profunda, porque los planes debieran ser inmutables (!) ya que React lo requiere
      // Al contrario, si se vuelve necesario hacer una copia profunda significa que hay un bug en algun lado porque se estan mutando datos que debieran ser inmutables.
      previousClasses.current = validatablePlan.classes
    } catch (err) {
      handleErrors(err)
    }
  }

  async function savePlan (): Promise<void> {
    if (validatablePlan == null) {
      toast.error('No se ha generado un plan aun')
      return
    }
    if (params?.plannerId != null) {
      setPlannerStatus(PlannerStatus.VALIDATING)
      try {
        await DefaultService.updatePlan(params.plannerId, validatablePlan)
        toast.success('Plan actualizado exitosamente.')
      } catch (err) {
        handleErrors(err)
      }
      setPlannerStatus(PlannerStatus.READY)
    } else {
      const planName = prompt('¿Cómo quieres llamarle a esta planificación?')
      if (planName == null || planName === '') return
      setPlannerStatus(PlannerStatus.VALIDATING)
      try {
        const res = await DefaultService.savePlan(planName, validatablePlan)
        toast.success('Plan guardado exitosamente, redireccionando...', {
          toastId: 'newPlanSaved',
          data: { planId: res.id }
        })
      } catch (err) {
        handleErrors(err)
      }
    }
    setPlannerStatus(PlannerStatus.READY)
  }

  function addCourse (semIdx: number): void {
    if (validatablePlan == null) {
      return
    }
    setModalData({
      equivalence: undefined,
      selector: true,
      semester: semIdx,
      index: validatablePlan.classes[semIdx].length
    })
    setIsModalOpen(true)
  }

  function remCourse (semIdx: number, code: string): void {
    if (validatablePlan === null) return
    let idx = -1
    for (let i = 0; i < validatablePlan.classes[semIdx].length; i++) {
      if (validatablePlan.classes[semIdx][i].code === code) {
        idx = i
        break
      }
    }
    if (idx === -1) return
    setValidatablePlan(prev => {
      if (prev === null) return prev
      const newClases = prev.classes
      newClases[semIdx].splice(idx, 1)
      while (newClases[newClases.length - 1].length === 0) {
        newClases.pop()
      }
      return { ...prev, classes: newClases }
    })
  }

  function moveCourse (drag: { name: string, code: string, index: number, semester: number, credits?: number, is_concrete?: boolean }, semester: number, index: number): void {
    if (validatablePlan === null) {
      return
    }
    setValidatablePlan(prev => {
      if (prev === null) return prev
      if (drag.is_concrete === true && semester !== drag.semester && semester < prev.classes.length && prev.classes[semester].map(course => course.code).includes(drag.code)) {
        toast.error('No se puede tener dos ramos iguales en un mismo semestre')
        return prev
      }
      const newClassesGrid = prev.classes
      if (semester - newClassesGrid.length >= 0) {
        if (semester - newClassesGrid.length > 0) newClassesGrid.push([])
        newClassesGrid.push([])
      }
      newClassesGrid[semester].splice(index, 0, newClassesGrid[drag.semester][drag.index])
      if (semester === drag.semester && index < drag.index) {
        newClassesGrid[drag.semester].splice(drag.index + 1, 1)
      } else {
        newClassesGrid[drag.semester].splice(drag.index, 1)
      }
      while (newClassesGrid[newClassesGrid.length - 1].length === 0) {
        newClassesGrid.pop()
      }
      return { ...prev, classes: newClassesGrid }
    })
  }

  async function loadCurriculumsData (cYear: string, cMajor?: string): Promise<void> {
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
    setCurriculumData(curriculumData)
  }

  async function openModal (equivalence: Equivalence | EquivalenceId, semester: number, index: number): Promise<void> {
    if ('courses' in equivalence) {
      setModalData({ equivalence, selector: false, semester, index })
    } else {
      const response = await DefaultService.getEquivalenceDetails([equivalence.code])
      setModalData({ equivalence: response[0], selector: false, semester, index })
    }
    setIsModalOpen(true)
  }

  async function closeModal (selection?: string): Promise<void> {
    if (selection != null && modalData !== undefined && validatablePlan != null) {
      const pastClass = validatablePlan.classes[modalData.semester][modalData.index]
      if (pastClass !== undefined && selection === pastClass.code) { setIsModalOpen(false); return }
      for (const existingCourse of validatablePlan.classes[modalData.semester].flat()) {
        if (existingCourse.code === selection) {
          toast.error(`${selection} ya se encuentra en este semestre, seleccione otro curso por favor`)
          return
        }
      }
      const details = (await DefaultService.getCourseDetails([selection]))[0]
      setCourseDetails((prev) => { return { ...prev, [details.code]: details } })

      const newValidatablePlan = validatablePlan
      if (modalData.equivalence === undefined) {
        newValidatablePlan.classes[modalData.semester][modalData.index] = {
          is_concrete: true,
          code: selection,
          equivalence: undefined
        }
      } else {
        const oldEquivalence = 'credits' in pastClass ? pastClass : pastClass.equivalence

        newValidatablePlan.classes[modalData.semester][modalData.index] = {
          is_concrete: true,
          code: selection,
          equivalence: oldEquivalence
        }
        if (oldEquivalence !== undefined && oldEquivalence.credits !== details.credits) {
          if (oldEquivalence.credits > details.credits) {
            newValidatablePlan.classes[modalData.semester].splice(modalData.index, 1,
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
            const semester = newValidatablePlan.classes[modalData.semester]
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
            newValidatablePlan.classes[modalData.semester].splice(modalData.index, 1,
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
      }
      setValidatablePlan(newValidatablePlan)
      setPlannerStatus(PlannerStatus.VALIDATING)
    }
    setIsModalOpen(false)
  }

  function reset (): void {
    setPlannerStatus(PlannerStatus.LOADING)
  }

  async function checkMinorForNewMajor (major: Major): Promise<void> {
    const newMinors = await DefaultService.getMinors(major.cyear, major.code)
    const isValidMinor = validatablePlan?.curriculum.minor === null || validatablePlan?.curriculum.minor === undefined || newMinors.some(m => m.code === validatablePlan?.curriculum.minor)
    if (!isValidMinor) {
      setPopUpAlert({
        title: 'Minor incompatible',
        desc: 'Advertencia: La selección del nuevo major no es compatible con el minor actual. Continuar con esta selección requerirá eliminar el minor actual. ¿Desea continuar y eliminar su minor?',
        major: major.code,
        isOpen: true
      })
    } else {
      await selectMajor(major.code, true)
    }
  }

  async function handlePopUpAlert (isCanceled: boolean): Promise<void> {
    const major = popUpAlert.major
    setPopUpAlert({ ...popUpAlert, isOpen: false })
    if (!isCanceled) {
      await selectMajor(major, false)
    }
  }

  async function selectMajor (majorCode: string, isMinorValid: boolean): Promise<void> {
    setValidatablePlan((prev) => {
      if (prev == null) return prev

      const newCurriculum = prev.curriculum
      const newClasses = prev.classes
      newCurriculum.major = majorCode
      newClasses.forEach((sem, idx) => {
        if (idx >= prev.next_semester) {
          newClasses[idx] = sem.filter((c, i) => {
            if (findCourseSuperblock(validationResult, idx, i) !== 'Major') {
              return c
            }
            return false
          })
        }
      })
      if (!isMinorValid) {
        newCurriculum.minor = undefined
        newClasses.forEach((sem, idx) => {
          if (idx >= prev.next_semester) {
            newClasses[idx] = sem.filter((c, i) => {
              if (findCourseSuperblock(validationResult, idx, i) !== 'Minor') {
                return c
              }
              return false
            })
          }
        })
      }
      return { ...prev, curriculum: newCurriculum }
    })
  }

  function selectMinor (minor: Minor): void {
    setValidatablePlan((prev) => {
      if (prev == null) return prev
      const newCurriculum = prev.curriculum
      const newClasses = prev.classes
      newCurriculum.minor = minor.code
      newClasses.forEach((sem, idx) => {
        if (idx >= prev.next_semester) {
          newClasses[idx] = sem.filter((c, i) => {
            if (findCourseSuperblock(validationResult, idx, i) !== 'Minor') {
              return c
            }
            return false
          })
        }
      })
      return { ...prev, curriculum: newCurriculum }
    })
  }

  function selectTitle (title: Title): void {
    setValidatablePlan((prev) => {
      if (prev == null) return prev
      const newCurriculum = prev.curriculum
      const newClasses = prev.classes
      newCurriculum.title = title.code
      newClasses.forEach((sem, idx) => {
        if (idx >= prev.next_semester) {
          newClasses[idx] = sem.filter((c, i) => {
            if (findCourseSuperblock(validationResult, idx, i) !== 'Title') {
              return c
            }
            return false
          })
        }
      })
      return { ...prev, curriculum: newCurriculum }
    })
  }

  useEffect(() => {
    setPlannerStatus(PlannerStatus.LOADING)
  }, [])

  useEffect(() => {
    console.log(plannerStatus)
    if (plannerStatus === 'LOADING') {
      void fetchData()
    } else if (plannerStatus === 'VALIDATING' && validatablePlan != null) {
      validate(validatablePlan).catch(err => {
        setValidationResult({
          diagnostics: [{
            is_warning: false,
            message: `Error interno: ${String(err)}`
          }],
          course_superblocks: validatablePlan.classes.map(sem => sem.map(c => ''))
        })
      })
    }
  }, [plannerStatus])

  useEffect(() => {
    if (validatablePlan != null) {
      const { major, minor, title } = validatablePlan.curriculum
      const curriculumChanged =
          major !== previousCurriculum.current.major ||
          minor !== previousCurriculum.current.minor ||
          title !== previousCurriculum.current.title
      if (curriculumChanged) {
        setPlannerStatus(PlannerStatus.LOADING)
      } else {
        setPlannerStatus(PlannerStatus.VALIDATING)
      }
    }
  }, [validatablePlan])
  return (
    <div className={`w-full h-full p-3 flex flex-grow overflow-hidden flex-row ${(plannerStatus !== 'ERROR' && plannerStatus !== 'READY') ? 'cursor-wait' : ''}`}>
      <DebugGraph validatablePlan={validatablePlan} />
      <CourseSelectorDialog equivalence={modalData?.equivalence} open={isModalOpen} onClose={async (selection?: string) => await closeModal(selection)}/>
      <AlertModal title={popUpAlert.title} desc={popUpAlert.desc} isOpen={popUpAlert.isOpen} close={handlePopUpAlert}/>
      {plannerStatus === 'LOADING' && (
        <Spinner message='Cargando planificación...' />
      )}

      {plannerStatus === 'ERROR' && (<div className={'w-full h-full flex flex-col justify-center items-center'}>
        <p className={'text-2xl font-semibold mb-4'}>Error al cargar plan</p>
        <p className={'text-sm font-normal'}>{error}</p>
      </div>)}

      {plannerStatus !== 'LOADING' && plannerStatus !== 'ERROR' && <>
        <div className={'flex flex-col w-5/6 flex-grow'}>
          {curriculumData != null && validatablePlan != null &&
            <CurriculumSelector
              planName={planName}
              curriculumData={curriculumData}
              validatablePlan={validatablePlan}
              selectMajor={checkMinorForNewMajor}
              selectMinor={selectMinor}
              selectTitle={selectTitle}
            />}
          <ControlTopBar
            reset={reset}
            save={savePlan}
            validating={plannerStatus !== 'READY'}
          />
          <DndProvider backend={HTML5Backend}>
            <PlanBoard
              classesGrid={validatablePlan?.classes ?? null}
              classesDetails={courseDetails}
              moveCourse={moveCourse}
              openModal={openModal}
              remCourse={remCourse}
              addCourse={addCourse}
              validating={plannerStatus !== 'READY'}
              validationResult={validationResult}
            />
          </DndProvider>
        </div>
        <ErrorTray diagnostics={validationResult?.diagnostics ?? []} validating={plannerStatus === 'VALIDATING'}/>
        </>}
    </div>
  )
}

export default Planner
