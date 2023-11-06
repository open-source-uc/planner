import { Spinner } from '../../components/Spinner'
import ErrorTray from './ErrorTray'
import PlanBoard from './planBoard/PlanBoard'
import ControlTopBar from './ControlTopBar'
import CourseSelectorDialog from './CourseSelectorDialog'
import LegendModal from './LegendModal'
import SavePlanModal from './SavePlanModal'
import CurriculumSelector from './CurriculumSelector'
import AlertModal from '../../components/AlertModal'
import { useParams } from '@tanstack/react-router'
import { useState, useEffect, useRef, useCallback, useMemo, useReducer } from 'react'
import { type CourseDetails, type Major, DefaultService, type ValidatablePlan, type EquivDetails, type EquivalenceId, type ValidationResult, type PlanView, type CancelablePromise } from '../../client'
import { type CourseId, type PseudoCourseDetail, type PseudoCourseId, type CurriculumData, type ModalData, type PlanDigest, type ValidationDigest, isApiError, isCancelError, isCourseRequirementErr, type Cyear } from './utils/Types'
import { validateCourseMovement, updateClassesState, getCoursePos } from './utils/planBoardFunctions'
import { useAuth } from '../../contexts/auth.context'
import { toast } from 'react-toastify'
import DebugGraph from '../../components/DebugGraph'
import deepEqual from 'fast-deep-equal'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import { collectRequirements } from './utils/utils'
import ReceivePaste from './utils/ReceivePaste'

enum PlannerStatus {
  LOADING = 'LOADING',
  CHANGING_CURRICULUM = 'CHANGING_CURRICULUM',
  VALIDATING = 'VALIDATING',
  SAVING = 'SAVING',
  ERROR = 'ERROR',
  READY = 'READY',
}

const reduceCourseDetails = (old: Record<string, PseudoCourseDetail>, add: Record<string, PseudoCourseDetail>): Record<string, PseudoCourseDetail> => {
  return { ...old, ...add }
}

/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */
const Planner = (): JSX.Element => {
  const [planName, setPlanName] = useState<string>('')
  const [planID, setPlanID] = useState<string | undefined>(useParams()?.plannerId)
  const [validatablePlan, setValidatablePlan] = useState<ValidatablePlan | null >(null)
  const [courseDetails, addCourseDetails] = useReducer(reduceCourseDetails, {})
  const courseDetailsRef = useRef(courseDetails)
  const [curriculumData, setCurriculumData] = useState<CurriculumData | null>(null)
  const [modalData, setModalData] = useState<ModalData>()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isLegendModalOpen, setIsLegendModalOpen] = useState(false)
  const [isSavePlanModalOpen, setIsSavePlanModalOpen] = useState(false)
  const [plannerStatus, setPlannerStatus] = useState<PlannerStatus>(PlannerStatus.LOADING)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [popUpAlert, setPopUpAlert] = useState<{ title: string, major?: string, year?: Cyear, deleteMajor: boolean, desc: string, isOpen: boolean }>({ title: '', major: '', deleteMajor: false, desc: '', isOpen: false })

  const previousCurriculum = useRef<{ major: string | undefined, minor: string | undefined, title: string | undefined, cyear?: Cyear }>({ major: '', minor: '', title: '' })
  const previousClasses = useRef<PseudoCourseId[][]>([[]])

  const [, setValidationPromise] = useState<CancelablePromise<any> | null>(null)

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

  // Calcular informacion util sobre la validacion cada vez que cambia
  const validationDigest = useMemo((): ValidationDigest => {
    const digest: ValidationDigest = {
      courses: [],
      semesters: [],
      isOutdated: false
    }
    if (validatablePlan != null) {
      // Initialize course information
      digest.courses = validatablePlan.classes.map((semester, i) => {
        return semester.map((course, j) => {
          const { code, instance } = planDigest.indexToId[i][j]
          const superblock = validationResult?.course_superblocks?.[code]?.[instance] ?? ''
          return {
            superblock,
            errorIndices: [],
            warningIndices: []
          }
        })
      })
      // Initialize semester information to an empty state
      digest.semesters = validatablePlan.classes.map(() => {
        return {
          errorIndices: [],
          warningIndices: []
        }
      })
      if (validationResult != null) {
        // Fill course and semester information with their associated errors
        for (let k = 0; k < validationResult.diagnostics.length; k++) {
          const diag = validationResult.diagnostics[k]
          if (diag.kind === 'outdated' || diag.kind === 'outdatedcurrent') {
            digest.isOutdated = true
          }
          if (diag.associated_to != null) {
            for (const assoc of diag.associated_to) {
              if (typeof assoc === 'number') {
                // This error is associated to a semester
                const semDigest = digest.semesters[assoc]
                if (semDigest != null) {
                  const diagIndices = diag.is_err ?? true ? semDigest.errorIndices : semDigest.warningIndices
                  diagIndices.push(k)
                }
              } else {
                // This error is associated to a course
                const semAndIdx = planDigest.idToIndex[assoc.code]?.[assoc.instance] ?? null
                if (semAndIdx != null) {
                  const [sem, idx] = semAndIdx
                  const courseDigest = digest.courses[sem][idx]
                  const diagIndices = diag.is_err ?? true ? courseDigest.errorIndices : courseDigest.warningIndices
                  diagIndices.push(k)
                }
              }
            }
          }
        }
      }
    }
    return digest
  }, [validatablePlan, planDigest, validationResult])

  const handleErrors = useCallback((err: unknown): void => {
    if (isApiError(err)) {
      console.error(err)
      switch (err.status) {
        case 401:
          console.log('token invalid or expired, loading re-login page')
          toast.error('Tu session a expirado. Redireccionando a pagina de inicio de sesion...', {
            toastId: 'ERROR401'
          })
          break
        case 403:
          toast.warn('No tienes permisos para realizar esa accion')
          break
        case 404:
          setError('El planner al que estas intentando acceder no existe o no es de tu propiedad')
          break
        case 429:
          toast.error('Se alcanzó el límite de actividad, espera y vuelve a intentarlo')
          return
        case 500:
          setError(err.message)
          break
        default:
          console.log(err.status)
          setError('Error desconocido')
          break
      }
      setPlannerStatus(PlannerStatus.ERROR)
    } else if (!isCancelError(err)) {
      setError('Error desconocido')
      console.error(err)
      setPlannerStatus(PlannerStatus.ERROR)
    }
  }, [])

  const getCourseDetails = useCallback(async (courses: PseudoCourseId[]): Promise<void> => {
    const pseudocourseCodes = new Set<string>()
    for (const courseid of courses) {
      const code = ('failed' in courseid ? courseid.failed : null) ?? courseid.code
      if (!(code in courseDetailsRef.current)) {
        pseudocourseCodes.add(code)
      }
      if ('equivalence' in courseid && courseid.equivalence != null) {
        const equivCode = courseid.equivalence.code
        if (!(equivCode in courseDetailsRef.current)) {
          pseudocourseCodes.add(equivCode)
        }
      }
    }
    if (pseudocourseCodes.size === 0) return
    console.log(`getting ${pseudocourseCodes.size} course details...`)
    try {
      const courseDetails = await DefaultService.getPseudocourseDetails(Array.from(pseudocourseCodes))
      const dict = courseDetails.reduce((acc: Record<string, PseudoCourseDetail>, curr: PseudoCourseDetail) => {
        if (curr == null) {
          // If there is an unknown code, ignore it instead of crashing
          return acc
        }
        acc[curr.code] = curr
        return acc
      }, {})
      addCourseDetails(dict)
    } catch (err) {
      handleErrors(err)
    }
  }, [handleErrors])

  const validate = useCallback(async (validatablePlan: ValidatablePlan): Promise<void> => {
    try {
      if (validatablePlan.classes.flat().length === 0) {
        setValidationPromise(prev => {
          if (prev != null) {
            prev.cancel()
            return null
          }
          return prev
        })
        previousClasses.current = validatablePlan.classes
        previousCurriculum.current = {
          major: validatablePlan.curriculum.major,
          minor: validatablePlan.curriculum.minor,
          title: validatablePlan.curriculum.title,
          cyear: validatablePlan.curriculum.cyear
        }
        setPlannerStatus(PlannerStatus.READY)
        return
      }
      const promise = authState?.user == null ? DefaultService.validateGuestPlan(validatablePlan) : DefaultService.validatePlanForUser(validatablePlan)
      setValidationPromise(prev => {
        if (prev != null) {
          prev.cancel()
        }
        return promise
      })
      const response = await promise
      setValidationPromise(null)
      previousCurriculum.current = {
        major: validatablePlan.curriculum.major,
        minor: validatablePlan.curriculum.minor,
        title: validatablePlan.curriculum.title,
        cyear: validatablePlan.curriculum.cyear
      }
      // Order diagnostics by putting errors first, then warnings.
      response.diagnostics.sort((a, b) => {
        if (a.is_err === b.is_err) {
          return 0
        } else if (a.is_err ?? true) {
          return -1
        } else {
          return 1
        }
      })
      const reqCourses = new Set<string>()
      for (const diag of response.diagnostics) {
        if (isCourseRequirementErr(diag)) {
          collectRequirements(diag.modernized_missing, reqCourses)
        }
      }
      if (reqCourses.size > 0) {
        await getCourseDetails(Array.from(reqCourses).map((code: string) => { return { code, isConcrete: true } }))
      }
      setValidationResult(prev => {
        // Validation often gives the same results after small changes
        // Avoid triggering changes if this happens
        if (deepEqual(prev, response)) return prev
        return response
      })
      setPlannerStatus(PlannerStatus.READY)
      previousClasses.current = validatablePlan.classes
    } catch (err) {
      handleErrors(err)
    }
  }, [authState?.user, getCourseDetails, handleErrors])

  const savePlan = useCallback(async (planName: string): Promise<void> => {
    if (validatablePlan == null) {
      toast.error('No se ha generado un plan aun')
      return
    }
    if (planID !== null && planID !== undefined) {
      setPlannerStatus(PlannerStatus.VALIDATING)
      try {
        await DefaultService.updatePlan(planID, validatablePlan)
        toast.success('Plan actualizado exitosamente.')
      } catch (err) {
        handleErrors(err)
      }
      setPlannerStatus(PlannerStatus.READY)
    } else {
      if (planName == null || planName === '') return
      setPlannerStatus(PlannerStatus.VALIDATING)
      try {
        const res = await DefaultService.savePlan(planName, validatablePlan)
        setPlanID(res.id)
        setPlanName(res.name)
        toast.success('Plan guardado exitosamente')
      } catch (err) {
        handleErrors(err)
      }
    }
    setPlannerStatus(PlannerStatus.READY)
  }, [handleErrors, planID, validatablePlan])

  const openModalForExtraClass = useCallback((semIdx: number): void => {
    setModalData({
      equivalence: undefined,
      selector: true,
      semester: semIdx
    })
    setIsModalOpen(true)
  }, []) // addCourse should not depend on `validatablePlan`, so that memoing does its work

  const remCourse = useCallback((course: CourseId): void => {
    // its ok to use `setValidatablePlan`
    // its not ok to use `validatablePlan` directly
    setValidatablePlan(prev => {
      if (prev === null) return null
      const remPos = getCoursePos(prev.classes, course)
      if (remPos === null) {
        toast.error('Index no encontrado')
        return prev
      }
      const newClases = [...prev.classes]
      const newClasesSem = [...prev.classes[remPos.semester]]
      newClasesSem.splice(remPos.index, 1)
      newClases[remPos.semester] = newClasesSem
      while (newClases[newClases.length - 1].length === 0) {
        newClases.pop()
      }
      return { ...prev, classes: newClases }
    })
  }, []) // remCourse should not depend on `validatablePlan`, so that memoing does its work

  const moveCourse = useCallback((drag: CourseId, drop: { semester: number, index: number }): void => {
    setValidatablePlan(prev => {
      if (prev === null) return prev
      const dragIndex = getCoursePos(prev.classes, drag)
      if (dragIndex === null) {
        toast.error('Index no encontrado')
        return prev
      }
      const validationError = validateCourseMovement(prev, dragIndex, drop)

      if (validationError !== null) {
        toast.error(validationError)
        return prev
      }
      return updateClassesState(prev, dragIndex, drop)
    })
  }, []) // moveCourse should not depend on `validatablePlan`, so that memoing does its work

  const loadCurriculumsData = useCallback(async (cYear: string, cMajor?: string): Promise<void> => {
    function listToRecord<T> (list: Array<T & { code: string }>): Record<string, T> {
      const dict: Record<string, T> = {}
      for (const item of list) {
        dict[item.code] = item
      }
      return dict
    }

    const { majors, minors, titles } = await (async () => {
      // if (curriculumData != null && curriculumData.ofCyear === cYear) {
      //  if (curriculumData.ofMajor === cMajor) {
      //    return curriculumData
      //  } else {
      //    return {
      //      majors: curriculumData.majors,
      //      minors: listToRecord(await DefaultService.getMinors(cYear, cMajor)),
      //      titles: curriculumData.titles
      //    }
      //  }
      // } else {
      const response = await DefaultService.getOffer(cYear, cMajor)
      return {
        majors: listToRecord(response.majors),
        minors: listToRecord(response.minors),
        titles: listToRecord(response.titles)
      }
      // }
    })()

    setCurriculumData({
      majors,
      minors,
      titles,
      ofMajor: cMajor,
      ofCyear: cYear
    })
  }, [])

  const getPlanById = useCallback(async (id: string): Promise<void> => {
    try {
      console.log('Getting Plan by Id...')
      const response: PlanView = await DefaultService.readPlan(id)
      previousClasses.current = response.validatable_plan.classes
      previousCurriculum.current = {
        major: response.validatable_plan.curriculum.major,
        minor: response.validatable_plan.curriculum.minor,
        title: response.validatable_plan.curriculum.title,
        cyear: response.validatable_plan.curriculum.cyear
      }
      await Promise.all([
        getCourseDetails(response.validatable_plan.classes.flat()),
        loadCurriculumsData(response.validatable_plan.curriculum.cyear, response.validatable_plan.curriculum.major),
        validate(response.validatable_plan)
      ])
      setValidatablePlan(response.validatable_plan)
      setPlanName(response.name)
      console.log('data loaded')
    } catch (err) {
      handleErrors(err)
    }
  }, [getCourseDetails, handleErrors, loadCurriculumsData, validate])

  const getDefaultPlan = useCallback(async (referenceValidatablePlan?: ValidatablePlan, truncateAt?: number): Promise<void> => {
    try {
      console.log('Getting Basic Plan...')
      let baseValidatablePlan
      if (referenceValidatablePlan === undefined || referenceValidatablePlan === null) {
        baseValidatablePlan = authState?.user == null ? await DefaultService.emptyGuestPlan() : await DefaultService.emptyPlanForUser()
      } else {
        baseValidatablePlan = { ...referenceValidatablePlan, classes: [...referenceValidatablePlan.classes] }
        truncateAt = truncateAt ?? (authState?.student?.next_semester ?? 0)
        baseValidatablePlan.classes.splice(truncateAt)
      }
      // truncate the validatablePlan to the last not empty semester
      while (baseValidatablePlan.classes.length > 0 && baseValidatablePlan.classes[baseValidatablePlan.classes.length - 1].length === 0) {
        baseValidatablePlan.classes.pop()
      }
      const response: ValidatablePlan = await DefaultService.generatePlan({
        passed: baseValidatablePlan,
        reference: referenceValidatablePlan ?? undefined
      })
      previousClasses.current = response.classes
      previousCurriculum.current = {
        major: response.curriculum.major,
        minor: response.curriculum.minor,
        title: response.curriculum.title,
        cyear: response.curriculum.cyear
      }
      await Promise.all([
        getCourseDetails(response.classes.flat()),
        loadCurriculumsData(response.curriculum.cyear, response.curriculum.major),
        validate(response)
      ])
      setValidatablePlan(response)
      console.log('data loaded')
    } catch (err) {
      handleErrors(err)
    }
  }, [authState?.student?.next_semester, authState?.user, getCourseDetails, handleErrors, loadCurriculumsData, validate])

  const fetchData = useCallback(async (): Promise<void> => {
    try {
      if (planID != null) {
        await getPlanById(planID)
      } else {
        await getDefaultPlan()
      }
    } catch (error) {
      setError('Hubo un error al cargar el planner')
      console.error(error)
      setPlannerStatus(PlannerStatus.ERROR)
    }
  }, [getDefaultPlan, getPlanById, planID])

  const loadNewPLan = useCallback(async (referenceValidatablePlan: ValidatablePlan): Promise<void> => {
    try {
      await getDefaultPlan(referenceValidatablePlan)
    } catch (error) {
      setError('Hubo un error al cargar el planner')
      console.error(error)
      setPlannerStatus(PlannerStatus.ERROR)
    }
  }, [getDefaultPlan])

  const openModal = useCallback(async (equivalence: EquivDetails | EquivalenceId, semester: number, index?: number): Promise<void> => {
    if ('courses' in equivalence) {
      setModalData({ equivalence, selector: false, semester, index })
    } else {
      const response = (await DefaultService.getPseudocourseDetails([equivalence.code]))[0]
      if (!('courses' in response)) {
        throw new Error('expected equivalence details')
      }
      setModalData({ equivalence: response, selector: false, semester, index })
    }
    setIsModalOpen(true)
  }, [])

  const closeModal = useCallback(async (selection?: CourseDetails): Promise<void> => {
    if (selection != null && modalData !== undefined) {
      addCourseDetails({ [selection.code]: selection })
      setValidatablePlan(prev => {
        if (prev === null) return prev
        const newValidatablePlan = { ...prev, classes: [...prev.classes] }
        while (newValidatablePlan.classes.length <= modalData.semester) {
          newValidatablePlan.classes.push([])
        }
        const index = modalData.index ?? newValidatablePlan.classes[modalData.semester].length
        const pastClass = newValidatablePlan.classes[modalData.semester][index]
        if (pastClass !== undefined && selection.code === pastClass.code) { setIsModalOpen(false); return prev }
        for (const existingCourse of newValidatablePlan.classes[modalData.semester].flat()) {
          if (existingCourse.code === selection.code) {
            toast.error(`${selection.name} ya se encuentra en este semestre, seleccione otro curso por favor`)
            return prev
          }
        }
        newValidatablePlan.classes[modalData.semester] = [...newValidatablePlan.classes[modalData.semester]]
        if (modalData.equivalence === undefined) {
          while (newValidatablePlan.classes.length <= modalData.semester) {
            newValidatablePlan.classes.push([])
          }
          newValidatablePlan.classes[modalData.semester][index] = {
            is_concrete: true,
            code: selection.code,
            equivalence: undefined
          }
        } else {
          const oldEquivalence = 'credits' in pastClass ? pastClass : pastClass.equivalence

          newValidatablePlan.classes[modalData.semester][index] = {
            is_concrete: true,
            code: selection.code,
            equivalence: oldEquivalence
          }
          if (oldEquivalence !== undefined && oldEquivalence.credits !== selection.credits) {
            if (oldEquivalence.credits > selection.credits) {
              newValidatablePlan.classes[modalData.semester].splice(index, 1,
                {
                  is_concrete: true,
                  code: selection.code,
                  equivalence: {
                    ...oldEquivalence,
                    credits: selection.credits
                  }
                },
                {
                  is_concrete: false,
                  code: oldEquivalence.code,
                  credits: oldEquivalence.credits - selection.credits
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
              let extra = selection.credits - oldEquivalence.credits
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
                  code: selection.code,
                  equivalence: {
                    ...oldEquivalence,
                    credits: selection.credits
                  }
                }
              )
            }
          }
        }
        setPlannerStatus(PlannerStatus.VALIDATING)
        setIsModalOpen(false)
        return newValidatablePlan
      })
    } else {
      setIsModalOpen(false)
    }
  }, [setValidatablePlan, setIsModalOpen, modalData])

  const openLegendModal = useCallback((): void => {
    setIsLegendModalOpen(true)
  }, [setIsLegendModalOpen])

  const closeLegendModal = useCallback((): void => {
    setIsLegendModalOpen(false)
  }, [setIsLegendModalOpen])

  const openSavePlanModal = useCallback(async (): Promise<void> => {
    if (planName == null || planName === '') {
      setIsSavePlanModalOpen(true)
    } else {
      await savePlan(planName)
    }
  }, [planName, savePlan])

  const closeSavePlanModal = useCallback((): void => {
    setIsSavePlanModalOpen(false)
  }, [])

  const reset = useCallback((): void => {
    setPlannerStatus(PlannerStatus.LOADING)
    setValidatablePlan(null)
  }, [])

  const selectYear = useCallback((cYear: Cyear, isMajorValid: boolean, isMinorValid: boolean): void => {
    setValidatablePlan((prev) => {
      if (prev == null || prev.curriculum.cyear === cYear) return prev
      const newCurriculum = { ...prev.curriculum, cyear: cYear }
      const newClasses = [...prev.classes]
      newClasses.splice(authState?.student?.next_semester ?? 0)
      if (!isMinorValid) {
        newCurriculum.minor = undefined
      }
      if (!isMajorValid) {
        newCurriculum.major = undefined
      }
      return { ...prev, classes: newClasses, curriculum: newCurriculum }
    })
  }, [setValidatablePlan, authState])

  // this sensitivity list shouldn't contain frequently-changing attributes
  const selectMajor = useCallback((majorCode: string | undefined, isMinorValid: boolean): void => {
    setValidatablePlan((prev) => {
      if (prev == null || prev.curriculum.major === majorCode) return prev
      const newCurriculum = { ...prev.curriculum, major: majorCode }
      if (!isMinorValid) {
        newCurriculum.minor = undefined
      }
      return { ...prev, curriculum: newCurriculum }
    })
  }, [setValidatablePlan]) // this sensitivity list shouldn't contain frequently-changing attributes

  const selectMinor = useCallback((minorCode: string | undefined): void => {
    setValidatablePlan((prev) => {
      if (prev == null || prev.curriculum.minor === minorCode) return prev
      const newCurriculum = { ...prev.curriculum, minor: minorCode }
      return { ...prev, curriculum: newCurriculum }
    })
  }, [setValidatablePlan]) // this sensitivity list shouldn't contain frequently-changing attributes

  const selectTitle = useCallback((titleCode: string | undefined): void => {
    setValidatablePlan((prev) => {
      if (prev == null || prev.curriculum.title === titleCode) return prev
      const newCurriculum = { ...prev.curriculum, title: titleCode }
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
        deleteMajor: false,
        isOpen: true
      })
    } else {
      selectMajor(major.code, true)
    }
  }, [validatablePlan?.curriculum, setPopUpAlert, selectMajor]) // this sensitivity list shouldn't contain frequently-changing attributes

  const checkMajorAndMinorForNewYear = useCallback(async (cyear: Cyear): Promise<void> => {
    const newMajors = await DefaultService.getMajors(cyear)
    const isValidMajor = validatablePlan?.curriculum.major === null || validatablePlan?.curriculum.major === undefined || newMajors.some(m => m.code === validatablePlan?.curriculum.major)

    if (!isValidMajor) {
      setPopUpAlert({
        title: 'Major incompatible',
        desc: 'Advertencia: La selección del nuevo año no es compatible con el major actual. Continuar con esta selección requerirá eliminar el major y minor actual. ¿Desea continuar y eliminar su minor?',
        year: cyear,
        deleteMajor: true,
        isOpen: true
      })
    } else {
      let isValidMinor = true
      if (validatablePlan?.curriculum.major !== null && validatablePlan?.curriculum.major !== undefined) {
        const newMinors = await DefaultService.getMinors(cyear, validatablePlan.curriculum.major)
        isValidMinor = validatablePlan?.curriculum.minor === null || validatablePlan?.curriculum.minor === undefined || newMinors.some(m => m.code === validatablePlan?.curriculum.minor)
      } if (!isValidMinor) {
        setPopUpAlert({
          title: 'Minor incompatible',
          desc: 'Advertencia: La selección del nuevo año no es compatible con el minor actual. Continuar con esta selección requerirá eliminar el minor actual. ¿Desea continuar y eliminar su minor?',
          year: cyear,
          deleteMajor: false,
          isOpen: true
        })
      } else {
        selectYear(cyear, true, true)
      }
    }
  }, [validatablePlan?.curriculum, setPopUpAlert, selectYear])

  const handlePopUpAlert = useCallback(async (isCanceled: boolean): Promise<void> => {
    setPopUpAlert(prev => {
      if (!isCanceled) {
        if ('major' in prev) selectMajor(prev.major, false)
        if ('year' in prev && prev.year !== undefined) {
          if (prev.deleteMajor) {
            selectYear(prev.year, false, false)
          } else {
            selectYear(prev.year, true, false)
          }
        }
      }
      return { ...prev, isOpen: false }
    })
  }, [setPopUpAlert, selectMajor, selectYear])

  useEffect(() => {
    setPlannerStatus(PlannerStatus.LOADING)
  }, [])

  useEffect(() => {
    console.log(`planner status set to ${plannerStatus}`)
    if (plannerStatus === 'LOADING') {
      void fetchData()
    }
  }, [plannerStatus, fetchData])

  useEffect(() => {
    if (validatablePlan != null) {
      const { major, minor, title, cyear } = validatablePlan.curriculum
      const curriculumChanged =
          major !== previousCurriculum.current.major ||
          minor !== previousCurriculum.current.minor ||
          title !== previousCurriculum.current.title ||
          cyear !== previousCurriculum.current.cyear
      if (curriculumChanged) {
        setPlannerStatus(PlannerStatus.CHANGING_CURRICULUM)
        void loadNewPLan(validatablePlan)
      } else {
        setPlannerStatus(prev => {
          if (prev === PlannerStatus.LOADING) return prev
          return PlannerStatus.VALIDATING
        })
        validate(validatablePlan).catch(err => {
          handleErrors(err)
        })
      }
    }
  }, [handleErrors, validatablePlan, validate, loadNewPLan])

  return (
    <div className={`w-full relative h-full flex flex-grow overflow-hidden flex-row ${(plannerStatus === 'LOADING') ? 'cursor-wait' : ''}`}>
      <DebugGraph validatablePlan={validatablePlan} />
      <ReceivePaste validatablePlan={validatablePlan} getDefaultPlan={getDefaultPlan} />
      <CourseSelectorDialog equivalence={modalData?.equivalence} open={isModalOpen} onClose={closeModal}/>
      <LegendModal open={isLegendModalOpen} onClose={closeLegendModal}/>
      <SavePlanModal isOpen={isSavePlanModalOpen} onClose={closeSavePlanModal} savePlan={savePlan}/>
      <AlertModal title={popUpAlert.title} isOpen={popUpAlert.isOpen} close={handlePopUpAlert}>{popUpAlert.desc}</AlertModal>
      {(plannerStatus === PlannerStatus.LOADING || plannerStatus === PlannerStatus.CHANGING_CURRICULUM) &&
        <div className="absolute w-screen h-full z-50 bg-white flex flex-col justify-center items-center">
          <Spinner message='Cargando planificación...' />
        </div>
      }

      {plannerStatus === 'ERROR'
        ? (<div className={'w-full h-full flex flex-col justify-center items-center'}>
            <p className={'text-2xl font-semibold mb-4'}>Error al cargar plan</p>
            <p className={'text-sm font-normal'}>{error}</p>
            <a href="https://github.com/open-source-uc/planner/issues?q=is%3Aopen+is%3Aissue+label%3Abug" className={'text-blue-700 underline text-sm'} rel="noreferrer" target="_blank">Reportar error</a>
          </div>)
        : <div className={'flex w-full p-3 pb-0'}>
            <div className={'flex flex-col overflow-auto flex-grow'}>
              <CurriculumSelector
                planName={planName}
                curriculumData={curriculumData}
                curriculumSpec={validatablePlan?.curriculum ?? { cyear: null, major: null, minor: null, title: null }}
                selectMajor={checkMinorForNewMajor}
                selectMinor={selectMinor}
                selectTitle={selectTitle}
                selectYear={checkMajorAndMinorForNewYear}
              />
              <ControlTopBar
                reset={reset}
                openSavePlanModal={openSavePlanModal}
                openLegendModal={openLegendModal}
              />
              <DndProvider backend={HTML5Backend}>
                <PlanBoard
                  classesGrid={validatablePlan?.classes ?? []}
                  planDigest={planDigest}
                  classesDetails={courseDetails}
                  moveCourse={moveCourse}
                  openModal={openModal}
                  addCourse={openModalForExtraClass}
                  remCourse={remCourse}
                  validationDigest={validationDigest}
                />
              </DndProvider>
            </div>
          <ErrorTray
            setValidatablePlan={setValidatablePlan}
            getCourseDetails={getCourseDetails}
            diagnostics={validationResult?.diagnostics ?? []}
            validating={plannerStatus === 'VALIDATING'}
            courseDetails={courseDetails}
          />
        </div>
      }
    </div>
  )
}

export default Planner
