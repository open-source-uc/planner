import { Spinner } from '../../components/Spinner'
import ErrorTray from './ErrorTray'
import PlanBoard from './planBoard/PlanBoard'
import ControlTopBar from './ControlTopBar'
import CourseSelectorDialog from './CourseSelectorDialog'
import CurriculumSelector from './CurriculumSelector'
import AlertModal from '../../components/AlertModal'
import { useParams } from '@tanstack/react-router'
import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import { ApiError, Major, Minor, Title, DefaultService, ValidatablePlan, CourseDetails, EquivDetails, ConcreteId, EquivalenceId, FlatValidationResult, PlanView } from '../../client'
import { useAuth } from '../../contexts/auth.context'
import { toast } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import DebugGraph from '../../components/DebugGraph'
import deepEqual from 'fast-deep-equal'

export type PseudoCourseId = ConcreteId | EquivalenceId
export type PseudoCourseDetail = CourseDetails | EquivDetails
export interface CurriculumData {
  majors: { [code: string]: Major }
  minors: { [code: string]: Minor }
  titles: { [code: string]: Title }
}

type ModalData = { equivalence: EquivDetails | undefined, selector: boolean, semester: number, index?: number } | undefined

enum PlannerStatus {
  LOADING = 'LOADING',
  VALIDATING = 'VALIDATING',
  SAVING = 'SAVING',
  ERROR = 'ERROR',
  READY = 'READY',
}

const isApiError = (err: any): err is ApiError => {
  return err.status !== undefined
}

export interface PlanDigest {
  // Maps `(code, course instance index)` to `(semester, index within semester)`
  idToIndex: { [code: string]: Array<[number, number]> }
  // Maps `(semester, index within semester)` to `(code, course instance index)`
  indexToId: Array<Array<{ code: string, instance: number }>>
}

export interface CourseValidationDigest {
  // Contains the superblock string
  // The empty string if no superblock is found
  superblock: string
  // Contains the indices of any errors associated with this course
  errorIndices: number[]
  // Contains the indices of any warnings associated with this course
  warningIndices: number[]
}

export type ValidationDigest = CourseValidationDigest[][]

/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */
const Planner = (): JSX.Element => {
  const [planName, setPlanName] = useState<string>('')
  const [validatablePlan, setValidatablePlan] = useState<ValidatablePlan | null >(null)
  const [courseDetails, setCourseDetails] = useState<{ [code: string]: PseudoCourseDetail }>({})
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

  const planDigest = useMemo((): PlanDigest => {
    const digest: PlanDigest = {
      idToIndex: {},
      indexToId: []
    }
    if (validatablePlan != null) {
      for (let i = 0; i < validatablePlan.classes.length; i++) {
        const idx2id = []
        for (let j = 0; j < validatablePlan.classes[i].length; j++) {
          const c = validatablePlan.classes[i][j]
          let reps = digest.idToIndex[c.code]
          if (reps === undefined) {
            reps = []
            digest.idToIndex[c.code] = reps
          }
          idx2id.push({ code: c.code, instance: reps.length })
          reps.push([i, j])
        }
        digest.indexToId.push(idx2id)
      }
    }
    return digest
  }, [validatablePlan])

  const validationDigest = useMemo((): ValidationDigest => {
    let digest: ValidationDigest = []
    if (validatablePlan != null) {
      digest = validatablePlan.classes.map((semester, i) => {
        return semester.map((course, j) => {
          const { code, instance } = planDigest.indexToId[i][j]
          const rawSuperblock = validationResult?.course_superblocks?.[code]?.[instance] ?? null
          const superblock = rawSuperblock === null ? '' : rawSuperblock.normalize('NFD').replace(/[\u0300-\u036f]/g, '').split(' ')[0]
          return {
            superblock,
            errorIndices: [],
            warningIndices: []
          }
        })
      })
      if (validationResult != null) {
        for (let k = 0; k < validationResult.diagnostics.length; k++) {
          const diag = validationResult.diagnostics[k]
          if (diag.class_id != null) {
            const semAndIdx = planDigest.idToIndex[diag.class_id.code]?.[diag.class_id.instance] ?? null
            if (semAndIdx != null) {
              const [sem, idx] = semAndIdx
              const diagIndices = diag.is_warning ? digest[sem][idx].warningIndices : digest[sem][idx].errorIndices
              diagIndices.push(k)
            }
          }
        }
      }
    }
    return digest
  }, [validatablePlan, planDigest, validationResult])

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
      } else {
        ValidatablePlan = { ...ValidatablePlan }
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
      const dict = courseDetails.flat().reduce((acc: { [code: string]: PseudoCourseDetail }, curr: PseudoCourseDetail) => {
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
      setValidationResult(prev => {
        // Validation often gives the same results after small changes
        // Avoid triggering changes if this happens
        if (deepEqual(prev, response)) return prev
        return response
      })
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
        console.log(res)
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

  const addCourse = useCallback((semIdx: number): void => {
    setModalData({
      equivalence: undefined,
      selector: true,
      semester: semIdx
    })
    setIsModalOpen(true)
  }, []) // addCourse should not depend on `validatablePlan`, so that memoing does its work

  const remCourse = useCallback((semIdx: number, index: number): void => {
    // its ok to use `setValidatablePlan`
    // its not ok to use `validatablePlan` directly
    setValidatablePlan(prev => {
      if (prev === null) return null
      const newClases = [...prev.classes]
      const newClasesSem = [...prev.classes[semIdx]]
      newClasesSem.splice(index, 1)
      newClases[semIdx] = newClasesSem
      while (newClases[newClases.length - 1].length === 0) {
        newClases.pop()
      }
      return { ...prev, classes: newClases }
    })
  }, []) // remCourse should not depend on `validatablePlan`, so that memoing does its work

  const moveCourse = useCallback((drag: { semester: number, index: number }, drop: { semester: number, index: number }): void => {
    // move course from drag.semester, drag.index to semester, index
    setValidatablePlan(prev => {
      if (prev === null) return prev
      const dragCourse = prev.classes[drag.semester][drag.index]
      if (dragCourse.is_concrete === true && drop.semester !== drag.semester && drop.semester < prev.classes.length && prev.classes[drop.semester].map(course => course.code).includes(dragCourse.code)) {
        toast.error('No se puede tener dos cursos iguales en un mismo semestre')
        return prev
      }
      const newClasses = [...prev.classes]
      while (drop.semester >= newClasses.length) {
        newClasses.push([])
      }
      newClasses[drop.semester].splice(drop.index, 0, newClasses[drag.semester][drag.index])
      if (drop.semester === drag.semester && drop.index < drag.index) {
        newClasses[drag.semester].splice(drag.index + 1, 1)
      } else {
        newClasses[drag.semester].splice(drag.index, 1)
      }
      console.log(newClasses, newClasses[newClasses.length - 1], newClasses[newClasses.length - 1].length === 0)
      while (newClasses[newClasses.length - 1].length === 0) {
        newClasses.pop()
      }
      return { ...prev, classes: newClasses }
    })
  }, []) // moveCourse should not depend on `validatablePlan`, so that memoing does its work

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

  const openModal = useCallback(async (equivalence: EquivDetails | EquivalenceId, semester: number, index?: number): Promise<void> => {
    if ('courses' in equivalence) {
      setModalData({ equivalence, selector: false, semester, index })
    } else {
      const response = await DefaultService.getEquivalenceDetails([equivalence.code])
      setModalData({ equivalence: response[0], selector: false, semester, index })
    }
    setIsModalOpen(true)
  }, [])

  async function closeModal (selection?: string): Promise<void> {
    if (selection != null && modalData !== undefined && validatablePlan != null) {
      let index = modalData.index
      if (index === undefined) {
        index = validatablePlan.classes[modalData.semester].length
      }
      const pastClass = validatablePlan.classes[modalData.semester][index]
      if (pastClass !== undefined && selection === pastClass.code) { setIsModalOpen(false); return }
      for (const existingCourse of validatablePlan.classes[modalData.semester].flat()) {
        if (existingCourse.code === selection) {
          toast.error(`${selection} ya se encuentra en este semestre, seleccione otro curso por favor`)
          return
        }
      }
      const details = (await DefaultService.getCourseDetails([selection]))[0]
      setCourseDetails((prev) => { return { ...prev, [details.code]: details } })

      const newValidatablePlan = { ...validatablePlan, classes: [...validatablePlan.classes] }
      newValidatablePlan.classes[modalData.semester] = [...newValidatablePlan.classes[modalData.semester]]
      if (modalData.equivalence === undefined) {
        newValidatablePlan.classes[modalData.semester][index] = {
          is_concrete: true,
          code: selection,
          equivalence: undefined
        }
      } else {
        const oldEquivalence = 'credits' in pastClass ? pastClass : pastClass.equivalence

        newValidatablePlan.classes[modalData.semester][index] = {
          is_concrete: true,
          code: selection,
          equivalence: oldEquivalence
        }
        if (oldEquivalence !== undefined && oldEquivalence.credits !== details.credits) {
          if (oldEquivalence.credits > details.credits) {
            newValidatablePlan.classes[modalData.semester].splice(index, 1,
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
                  semester.splice(index, 1)
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
            newValidatablePlan.classes[modalData.semester].splice(index, 1,
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

  const selectMajor = useCallback(async (majorCode: string, isMinorValid: boolean): Promise<void> => {
    setValidatablePlan((prev) => {
      if (prev == null) return prev
      const newCurriculum = { ...prev.curriculum, major: majorCode }
      prev.classes.splice(prev.next_semester)
      if (!isMinorValid) {
        newCurriculum.minor = undefined
      }
      return { ...prev, curriculum: newCurriculum }
    })
  }, [setValidatablePlan]) // this sensitivity list shouldn't contain frequently-changing attributes

  const selectMinor = useCallback((minor: Minor): void => {
    setValidatablePlan((prev) => {
      if (prev == null) return prev
      const newCurriculum = { ...prev.curriculum, minor: minor.code }
      prev.classes.splice(prev.next_semester)
      return { ...prev, curriculum: newCurriculum }
    })
  }, [setValidatablePlan]) // this sensitivity list shouldn't contain frequently-changing attributes

  const selectTitle = useCallback((title: Title): void => {
    setValidatablePlan((prev) => {
      if (prev == null) return prev
      const newCurriculum = { ...prev.curriculum, title: title.code }
      prev.classes.splice(prev.next_semester)
      return { ...prev, curriculum: newCurriculum }
    })
  }, [setValidatablePlan]) // this sensitivity list shouldn't contain frequently-changing attributes

  const checkMinorForNewMajor = useCallback(async (major: Major): Promise<void> => {
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
  }, [validatablePlan?.curriculum, setPopUpAlert, selectMajor]) // this sensitivity list shouldn't contain frequently-changing attributes

  async function handlePopUpAlert (isCanceled: boolean): Promise<void> {
    const major = popUpAlert.major
    setPopUpAlert({ ...popUpAlert, isOpen: false })
    if (!isCanceled) {
      await selectMajor(major, false)
    }
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
        handleErrors(err)
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
      <CourseSelectorDialog equivalence={modalData?.equivalence} open={isModalOpen} onClose={closeModal}/>
      <AlertModal title={popUpAlert.title} desc={popUpAlert.desc} isOpen={popUpAlert.isOpen} close={handlePopUpAlert}/>
      {plannerStatus === 'LOADING' && (
        <div className="fixed left-0 w-screen h-full z-50 bg-white flex flex-col justify-center items-center">
          <Spinner message='Cargando planificación...' />
        </div>
      )}

      {plannerStatus === 'ERROR'
        ? (<div className={'w-full h-full flex flex-col justify-center items-center'}>
            <p className={'text-2xl font-semibold mb-4'}>Error al cargar plan</p>
            <p className={'text-sm font-normal'}>{error}</p>
          </div>)
        : <div className={'flex w-full'}>
            <div className={`flex flex-col overflow-auto flex-grow  ${plannerStatus !== PlannerStatus.READY ? 'pointer-events-none' : ''} `}>
              <CurriculumSelector
                planName={planName}
                curriculumData={curriculumData}
                curriculumSpec={validatablePlan?.curriculum ?? { cyear: null, major: null, minor: null, title: null }}
                selectMajor={checkMinorForNewMajor}
                selectMinor={selectMinor}
                selectTitle={selectTitle}
              />
              <ControlTopBar
                reset={reset}
                save={savePlan}
                validating={plannerStatus !== 'READY'}
              />
              <DndProvider backend={HTML5Backend}>
                {(validatablePlan != null) &&
                  <PlanBoard
                    classesGrid={validatablePlan.classes}
                    classesDetails={courseDetails}
                    moveCourse={moveCourse}
                    openModal={openModal}
                    addCourse={addCourse}
                    remCourse={remCourse}
                    validationDigest={validationDigest}
                  />}
              </DndProvider>
            </div>
          <ErrorTray diagnostics={validationResult?.diagnostics ?? []} validating={plannerStatus === 'VALIDATING'}/>
        </div>
      }
    </div>
  )
}

export default Planner
