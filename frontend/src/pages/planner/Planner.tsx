import { Spinner } from '../../components/Spinner'
import ErrorTray from './ErrorTray'
import PlanBoard from './planBoard/PlanBoard'
import ControlTopBar from './ControlTopBar'
import CourseSelectorDialog from './dialogs/CourseSelectorDialog'
import LegendModal from './dialogs/LegendModal'
import SavePlanModal from './dialogs/SavePlanModal'
import CurriculumSelector from './CurriculumSelector'
import AlertModal from '../../components/AlertModal'
import { useParams, Navigate, useNavigate } from '@tanstack/react-router'
import { useState, useEffect, useRef, useCallback, useMemo, useReducer, Fragment } from 'react'
import { type CourseDetails, type Major, DefaultService, type ValidatablePlan, type EquivDetails, type EquivalenceId, type ValidationResult, type PlanView, type CancelablePromise } from '../../client'
import { type CourseId, type PseudoCourseDetail, type PseudoCourseId, type CurriculumData, type ModalData, type PlanDigest, type ValidationDigest, type Cyear } from './utils/Types'
import { validateCourseMovement, updateClassesState, getCoursePos } from './utils/PlanBoardFunctions'
import { useAuth } from '../../contexts/auth.context'
import { toast } from 'react-toastify'
import DebugGraph from '../../components/DebugGraph'
import deepEqual from 'fast-deep-equal'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import { orderValidationDiagnostics, collectRequiredCourses, handleEmptyPlan, getValidationPromise, handleErrors, PlannerStatus, handleSelectEquivalence } from './utils/utils'
import { updateCurriculum, isMinorValid, isMajorValid, loadCurriculumsData } from './utils/CurriculumUtils'
import ReceivePaste from './utils/ReceivePaste'
import Banner from '../../components/Banner'
import useContextMenu from '../../utils/useContextMenu'
import useDummyModal from '../../utils/useDummyModal'

const reduceCourseDetails = (old: Record<string, PseudoCourseDetail>, add: Record<string, PseudoCourseDetail>): Record<string, PseudoCourseDetail> => {
  return { ...old, ...add }
}

/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */
const Planner = (): JSX.Element => {
  const [planName, setPlanName] = useState<string>('')
  const [validatablePlan, setValidatablePlan] = useState<ValidatablePlan | null >(null)
  const [curriculumData, setCurriculumData] = useState<CurriculumData | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [plannerStatus, setPlannerStatus] = useState<PlannerStatus>(PlannerStatus.LOADING)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [popUpAlert, setPopUpAlert] = useState<{ title: string, major?: string, year?: Cyear, deleteMajor: boolean, desc: string, isOpen: boolean }>({ title: '', major: '', deleteMajor: false, desc: '', isOpen: false })
  const [modalData, setModalData] = useState<ModalData>()
  const [, setValidationPromise] = useState<CancelablePromise<any> | null>(null)

  const [courseDetails, addCourseDetails] = useReducer(reduceCourseDetails, {})

  const { clicked } = useContextMenu()

  const { isModalOpen: isLegendModalOpen, openModal: openLegendModal, closeModal: closeLegendModal } = useDummyModal()
  const { isModalOpen: isSavePlanModalOpen, openModal: openSavePlanModal, closeModal: closeSavePlanModal } = useDummyModal()

  const previousCurriculum = useRef<{ major: string | undefined, minor: string | undefined, title: string | undefined, cyear?: Cyear }>({ major: '', minor: '', title: '' })
  const previousClasses = useRef<PseudoCourseId[][]>([[]])

  const planID = useParams()?.plannerId
  const impersonateRut = useParams()?.userRut

  const authState = useAuth()

  const navigate = useNavigate()

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

  const getCourseDetails = useCallback(async (courses: PseudoCourseId[]): Promise<void> => {
    console.log('Getting Courses Details...')
    const pseudocourseCodes = new Set<string>()
    for (const courseid of courses) {
      const code = ('failed' in courseid ? courseid.failed : null) ?? courseid.code
      // if (!(code in courseDetails)) {
      pseudocourseCodes.add(code)
      // }
    }
    if (pseudocourseCodes.size === 0) return
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
      handleErrors(err, setPlannerStatus, setError)
    }
  }, [])

  const validate = useCallback(async (validatablePlan: ValidatablePlan): Promise<void> => {
    try {
      if (validatablePlan.classes.flat().length === 0) {
        handleEmptyPlan(validatablePlan, setValidationPromise, previousClasses, previousCurriculum)
        setPlannerStatus(PlannerStatus.READY)
        return
      }

      const promise = getValidationPromise(validatablePlan, authState, impersonateRut)

      setValidationPromise((prev) => {
        if (prev != null) {
          prev.cancel()
        }
        return promise
      })

      const response = await promise
      orderValidationDiagnostics(response)
      const reqCourses = collectRequiredCourses(response.diagnostics)

      if (reqCourses.length > 0) {
        await getCourseDetails(reqCourses)
      }

      setValidationResult((prev) => {
        if (deepEqual(prev, response)) return prev
        return response
      })
      setPlannerStatus(PlannerStatus.READY)
    } catch (err) {
      handleErrors(err, setPlannerStatus, setError)
    }
  }, [authState, impersonateRut, getCourseDetails])

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
        handleErrors(err, setPlannerStatus, setError)
      }
    } else {
      if (planName === null || planName === '') return
      setPlannerStatus(PlannerStatus.VALIDATING)
      try {
        const res = await DefaultService.savePlan(planName, validatablePlan)
        const planId = res.id
        toast.success('Plan guardado exitosamente')
        await navigate({ to: '/planner/$planId', params: { planId } })
      } catch (err) {
        handleErrors(err, setPlannerStatus, setError)
      }
    }
    closeSavePlanModal()
    setPlannerStatus(PlannerStatus.READY)
  }, [planID, navigate, closeSavePlanModal, validatablePlan])

  const remCourse = useCallback((course: CourseId): void => {
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
  }, [])

  const getPlanById = useCallback(async (id: string): Promise<void> => {
    try {
      console.log('Getting Plan by Id...')
      let response: PlanView
      if (authState?.isMod === true) {
        response = await DefaultService.readAnyPlan(id)
      } else {
        response = await DefaultService.readPlan(id)
      }
      previousClasses.current = response.validatable_plan.classes
      previousCurriculum.current = {
        major: response.validatable_plan.curriculum.major,
        minor: response.validatable_plan.curriculum.minor,
        title: response.validatable_plan.curriculum.title,
        cyear: response.validatable_plan.curriculum.cyear
      }
      await Promise.all([
        getCourseDetails(response.validatable_plan.classes.flat()),
        loadCurriculumsData(response.validatable_plan.curriculum.cyear, setCurriculumData, response.validatable_plan.curriculum.major),
        validate(response.validatable_plan)
      ])
      setValidatablePlan(response.validatable_plan)
      setPlanName(response.name)
      console.log('data loaded')
    } catch (err) {
      handleErrors(err, setPlannerStatus, setError)
    }
  }, [authState?.isMod, getCourseDetails, validate])

  const getDefaultPlan = useCallback(async (referenceValidatablePlan?: ValidatablePlan, truncateAt?: number): Promise<void> => {
    try {
      console.log('Getting Basic Plan...')
      let baseValidatablePlan
      if (referenceValidatablePlan === undefined || referenceValidatablePlan === null) {
        baseValidatablePlan = authState?.user == null
          ? await DefaultService.emptyGuestPlan()
          : (authState?.isMod === true && impersonateRut != null) ? await DefaultService.emptyPlanForAnyUser(impersonateRut) : await DefaultService.emptyPlanForUser()
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
        loadCurriculumsData(response.curriculum.cyear, setCurriculumData, response.curriculum.major),
        validate(response)
      ])
      setValidatablePlan(response)
      console.log('data loaded')
    } catch (err) {
      handleErrors(err, setPlannerStatus, setError)
    }
  }, [authState?.student?.next_semester, impersonateRut, authState?.isMod, authState?.user, getCourseDetails, validate])

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

  const openModalForExtraClass = useCallback((semIdx: number): void => {
    setModalData({
      equivalence: undefined,
      selector: true,
      semester: semIdx
    })
    setIsModalOpen(true)
  }, [])

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
    if (selection == null || modalData === undefined) {
      setIsModalOpen(false)
      return
    }
    addCourseDetails({ [selection.code]: selection })
    setValidatablePlan(prev => {
      if (prev === null) return prev
      return handleSelectEquivalence(selection, prev, modalData)
    })
    setPlannerStatus(PlannerStatus.VALIDATING)
    setIsModalOpen(false)
  }, [modalData])

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

  const checkMinorForNewMajor = useCallback(async (major: Major): Promise<void> => {
    const isValidMinor = await isMinorValid(major.cyear, major.code, validatablePlan?.curriculum.minor)
    if (!isValidMinor) {
      setPopUpAlert({
        title: 'Minor incompatible',
        desc: 'Advertencia: La selección del nuevo major no es compatible con el minor actual. Continuar con esta selección requerirá eliminar el minor actual. ¿Desea continuar y eliminar su minor?',
        major: major.code,
        deleteMajor: false,
        isOpen: true
      })
    } else {
      setValidatablePlan(prev => {
        return updateCurriculum(prev, 'major', major.code, true)
      })
    }
  }, [validatablePlan?.curriculum, setPopUpAlert]) // this sensitivity list shouldn't contain frequently-changing attributes

  const handlePopUpAlert = useCallback(async (isCanceled: boolean): Promise<void> => {
    setPopUpAlert(prev => {
      if (!isCanceled) {
        if ('major' in prev) {
          setValidatablePlan(prevPlan => {
            return updateCurriculum(prevPlan, 'major', prev.major, false)
          })
        }
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
  }, [selectYear])

  const checkMajorAndMinorForNewYear = useCallback(async (cyear: Cyear): Promise<void> => {
    const isValidMajor = await isMajorValid(cyear, validatablePlan?.curriculum.major)
    if (!isValidMajor) {
      setPopUpAlert({
        title: 'Major incompatible',
        desc: 'Advertencia: La selección del nuevo año no es compatible con el major actual. Continuar con esta selección requerirá eliminar el major y minor actual. ¿Desea continuar y eliminar su minor?',
        year: cyear,
        deleteMajor: true,
        isOpen: true
      })
    } else {
      const isValidMinor = await isMinorValid(cyear, validatablePlan?.curriculum.major, validatablePlan?.curriculum.minor)
      if (!isValidMinor) {
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

  const selectMinor = useCallback((minorCode: string | undefined): void => {
    setValidatablePlan(prev => {
      return updateCurriculum(prev, 'minor', minorCode, true)
    })
  }, []) // this sensitivity list shouldn't contain frequently-changing attributes

  const selectTitle = useCallback((titleCode: string | undefined): void => {
    setValidatablePlan(prev => {
      return updateCurriculum(prev, 'title', titleCode, true)
    })
  }, [])

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
          handleErrors(err, setPlannerStatus, setError)
        })
      }
    }
  }, [validatablePlan, validate, loadNewPLan])

  if (impersonateRut !== authState?.student?.rut && impersonateRut !== undefined && authState?.isMod === true) {
    return <Navigate to="/mod/users"/>
  }

  return (
    <Fragment>
      {authState?.isMod === true &&
        <Banner bannerType={'Warning'} text={'Estás en una visualización exclusiva para moderadores. Puedes ver e interactuar con los planes del estudiante, pero no puedes guardar los cambios realizados.'}/>
      }
      {clicked && (
        <div>
          <ul>
            <li>Edit</li>
            <li>Copy</li>
            <li>Delete</li>
          </ul>
        </div>
      )}
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
                  openSavePlanModal={planID === undefined ? openSavePlanModal : savePlan}
                  openLegendModal={openLegendModal}
                  isMod={authState?.isMod === true}
                />
                <DndProvider backend={HTML5Backend}>
                  <PlanBoard
                    classesGrid={validatablePlan?.classes ?? []}
                    planDigest={planDigest}
                    classesDetails={courseDetails}
                    moveCourse={moveCourse}
                    openModal={openModal}
                    authState={authState}
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
    </Fragment>
  )
}

export default Planner
