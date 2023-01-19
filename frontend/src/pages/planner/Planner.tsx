import ErrorTray from './ErrorTray'
import PlanBoard from './planBoard/PlanBoard'
import { useState, useEffect, useRef } from 'react'
import { DefaultService, ValidatablePlan, Course, ConcreteId, EquivalenceId, FlatValidationResult } from '../../client'

type PseudoCourse = ConcreteId | EquivalenceId

/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */

const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<ValidatablePlan >({ classes: [], next_semester: 0 })
  const [courseDetails, setCourseDetails] = useState<{ [code: string]: Course }>({})
  const previousClasses = useRef<PseudoCourse[][]>([[]])
  const [loading, setLoading] = useState(true)
  const [validating, setValidanting] = useState(false)
  const [validationResult, setValidationResult] = useState<FlatValidationResult | null>(null)

  async function getCourseDetails (courses: PseudoCourse[]): Promise<void> {
    setValidanting(true)
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
    console.log('Details loaded')
    setValidanting(false)
  }

  async function validate (plan: ValidatablePlan): Promise<void> {
    setValidanting(true)
    console.log('validating...')
    const response = await DefaultService.validatePlan(plan)
    setValidationResult(response)
    console.log('validated')
    // keep a copy of the classes to compare with the next validation
    previousClasses.current = plan.classes
    setValidanting(false)
  }

  async function addCourse (semIdx: number): Promise<void> {
    const courseCodeRaw = prompt('Course code?')
    if (courseCodeRaw == null || courseCodeRaw === '') return
    const courseCode = courseCodeRaw.toUpperCase()
    for (const existingCourse of plan?.classes.flat()) {
      if (existingCourse.code === courseCode) {
        alert(`${courseCode} already on plan`)
        return
      }
    }
    setValidanting(true)
    try {
      const response = await DefaultService.getCourseDetails([courseCode])
      setCourseDetails((prev) => { return { ...prev, [response[0].code]: response[0] } })
      setPlan((prev) => {
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
    setValidanting(false)
  }

  useEffect(() => {
    const getBasicPlan = async (): Promise<void> => {
      console.log('getting Basic Plan...')
      const response = await DefaultService.generatePlan({
        classes: [],
        next_semester: 0,
        level: 1,
        school: 'Ingenieria',
        career: 'Ingenieria'
      })
      setPlan(response)
      await getCourseDetails(response.classes.flat()).catch(err => {
        setValidationResult({
          diagnostics: [{
            is_warning: false,
            message: `Internal error: ${String(err)}`
          }],
          course_superblocks: {}
        })
      })
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
    getBasicPlan().catch(err => {
      console.log(err)
    })
  }, [])

  useEffect(() => {
    if (!loading) {
      // dont validate if the classes are rearranging the same semester at previous validation
      let changed = plan.classes.length !== previousClasses.current.length
      if (!changed) {
        for (let idx = 0; idx < plan.classes.length; idx++) {
          const cur = [...plan.classes[idx]].sort((a, b) => a.code.localeCompare(b.code))
          const prev = [...previousClasses.current[idx]].sort((a, b) => a.code.localeCompare(b.code))
          if (JSON.stringify(cur) !== JSON.stringify(prev)) {
            changed = true
            break
          }
        }
      }
      if (changed) {
        validate(plan).catch(err => {
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
    <div className={`w-full h-full pb-10 flex flex-row border-red-400 border-2 ${validating ? 'cursor-wait' : ''}`}>
      {(!loading)
        ? <>
        <div className={'flex flex-col w-5/6'}>

        <ul className={'w-full mb-1 mt-2'}>
            <li className={'inline text-md ml-3 mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Titulo:</div> Civil de Industrias, Diploma en Ingeniería de Computación</li>
            <li className={'inline text-md mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Major:</div> Ingeniería y Ciencias Ambientales</li>
            <li className={'inline text-md mr-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Minor:</div> Amplitud en Programación</li>
          </ul>
          <PlanBoard
            plan={plan}
            courseDetails={courseDetails}
            setPlan={setPlan}
            addCourse={addCourse}
            validating={validating}
            validationResult={validationResult}
          />
        </div>
        <ErrorTray diagnostics={validationResult?.diagnostics ?? []} />
        </>
        : <div>Loading</div>}
    </div>
  )
}

export default Planner
