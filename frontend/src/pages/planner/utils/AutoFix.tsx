import { type CourseRequirementErr, type CurriculumErr, type Cyear, type MismatchedCyearErr, type OutdatedCurrentSemesterErr, type OutdatedPlanErr, type ValidatablePlan, type ValidationResult } from '../../../client'
import { type AuthState, useAuth } from '../../../contexts/auth.context'
import { type PseudoCourseId } from './Types'
import { getCourseName } from '../ErrorTray'
type Diagnostic = ValidationResult['diagnostics'][number]
type RequirementExpr = CourseRequirementErr['missing']

export const collectRequirements = (expr: RequirementExpr, into: Set<string>): void => {
  switch (expr.expr) {
    case 'and': case 'or':
      for (const child of expr.children) {
        collectRequirements(child, into)
      }
      break
    case 'req':
      into.add(expr.code)
      break
  }
}

const validateCyear = (raw: string): Cyear | null => {
    // Ensure that an array stays in sync with a union of string literals
    // https://stackoverflow.com/a/70694878/5884836
    type ValueOf<T> = T[keyof T]
    type NonEmptyArray<T> = [T, ...T[]]
    type MustInclude<T, U extends T[]> = [T] extends [ValueOf<U>] ? U : never
    function stringUnionToArray<T> () {
      return <U extends NonEmptyArray<T>>(...elements: MustInclude<T, U>) => elements
    }

    const validCyears = stringUnionToArray<Cyear['raw']>()('C2020')
    for (const cyear of validCyears) {
      if (raw === cyear) {
        return { raw: cyear }
      }
    }
    return null
}

const findSemesterWithLeastCourses = (newClasses: ValidatablePlan['classes'], auth: AuthState | null, until: number | null): number => {
  const nextSemester = auth?.student?.next_semester ?? 0
  while (newClasses.length <= nextSemester) newClasses.push([])
  let minSem = nextSemester
  for (let i = nextSemester; i < (until ?? newClasses.length); i++) {
    if (newClasses[i].length <= newClasses[minSem].length) minSem = i
  }
  return minSem
}

const fixMissingCurriculumCourse = (plan: ValidatablePlan, diag: CurriculumErr, fillWith: PseudoCourseId, auth: AuthState | null): ValidatablePlan => {
  // Add the recommended course to wherever there's fewer courses
  const nextSemester = auth?.student?.next_semester ?? 0
  const newClasses = [...plan.classes]
  while (newClasses.length <= nextSemester) newClasses.push([])
  const semIdx = findSemesterWithLeastCourses(newClasses, auth, null)
  // Add the recommended course to this semester
  newClasses[semIdx] = [...newClasses[semIdx]]
  newClasses[semIdx].push(fillWith)
  return { ...plan, classes: newClasses }
}

const fixIncorrectCyear = (plan: ValidatablePlan, diag: MismatchedCyearErr): ValidatablePlan => {
  // Change the cyear to whatever the user's cyear is
  const cyear = validateCyear(diag.user)
  if (cyear != null) {
    return { ...plan, curriculum: { ...plan.curriculum, cyear } }
  } else {
    return plan
  }
}

const fixOutdatedPlan = (plan: ValidatablePlan, diag: OutdatedPlanErr | OutdatedCurrentSemesterErr, auth: AuthState | null): ValidatablePlan => {
  if (auth == null) return plan
  // Update all outdated semesters
  const newClasses = [...plan.classes]
  for (const semIdx of diag.associated_to) {
    const passedSem = auth.student?.passed_courses?.[semIdx]
    if (passedSem != null) {
      newClasses[semIdx] = passedSem
    }
  }
  return { ...plan, classes: newClasses }
}

const addCourseAt = (plan: ValidatablePlan, code: string, onSem: number): ValidatablePlan => {
  const newClasses = [...plan.classes]
  while (newClasses.length <= onSem) newClasses.push([])
  newClasses[onSem] = [...newClasses[onSem]]
  newClasses[onSem].unshift({ is_concrete: true, code })
  return { ...plan, classes: newClasses }
}

const moveCourseByCode = (plan: ValidatablePlan, code: string, repIdx: number, toSem: number): ValidatablePlan => {
  // Find the course within the plan
  let semIdx = null
  let courseIdx = null
  let course = null
  for (let i = 0; i < plan.classes.length; i++) {
    const sem = plan.classes[i]
    for (let j = 0; j < sem.length; j++) {
      if (sem[j].code === code) {
        if (repIdx === 0) {
          semIdx = i
          courseIdx = j
          course = sem[j]
          i = plan.classes.length
          break
        } else {
          repIdx--
        }
      }
    }
  }
  console.log(code, repIdx, semIdx, courseIdx, course)
  if (semIdx == null || courseIdx == null || course == null) return plan
  if (semIdx === toSem) return plan

  // Create a new plan with the moved course
  const newClasses = [...plan.classes]
  newClasses[semIdx] = [...newClasses[semIdx]]
  newClasses[semIdx].splice(courseIdx, 1)
  while (newClasses.length <= toSem) newClasses.push([])
  newClasses[toSem] = [...newClasses[toSem]]
  newClasses[toSem].unshift(course)
  return { ...plan, classes: newClasses }
}

interface AutoFixProps {
  diag: Diagnostic
  setValidatablePlan: Function
  getCourseDetails: Function
  reqCourses: any
}

/**
 * Get the quick fixed for some diagnostic, if any.
 */
const AutoFix = ({ diag, setValidatablePlan, getCourseDetails, reqCourses }: AutoFixProps): JSX.Element => {
  // FIXME: TODO: Los cursos añadidos a traves del autofix les faltan los CourseDetails.
  // No me manejo bien con la implementación del frontend, lo dejo en mejores manos.
  const auth = useAuth()
  switch (diag.kind) {
    case 'curr': {
      const buttons = diag.fill_options.map(([fillWith, fillWithName], i) => (
        <button key={i} className="autofix" onClick={() => {
          setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
            if (plan == null) return null
            const planArreglado = fixMissingCurriculumCourse(plan, diag, fillWith, auth)
            void getCourseDetails(planArreglado.classes.flat())
            return planArreglado
          })
        }}>
          Agregar {fillWithName}
        </button>))
      return <>{buttons}</>
    }
    case 'cyear':
      if (validateCyear(diag.user) != null) {
        return <button className="autofix" onClick={() => {
          setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
            if (plan == null) return null
            return fixIncorrectCyear(plan, diag)
          })
        }}>Cambiar a {diag.user}</button>
      } else {
        return <></>
      }
    case 'outdated':
    case 'outdatedcurrent':
      if (auth != null) {
        return <button className="autofix" onClick={() => {
          setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
            if (plan == null) return null
            const planArreglado = fixOutdatedPlan(plan, diag, auth)
            void getCourseDetails(planArreglado.classes)
            return planArreglado
          })
        }}>Actualizar semestres {diag.associated_to.map(s => s + 1).join(', ')}</button>
      } else {
        return <></>
      }
    case 'req': {
      const buttons = []
      // Push back course itself
      const pushBackTo = diag.push_back
      if (pushBackTo != null) {
        buttons.push(<button key={buttons.length} className="autofix" onClick={() => {
          setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
            if (plan == null) return null
            console.log(diag.associated_to[0])
            return moveCourseByCode(plan, diag.associated_to[0].code, diag.associated_to[0].instance, pushBackTo)
          })
        }}>
          Atrasar curso  {getCourseName(diag.associated_to[0])}
        </button>)
      }
      // Pull requirements forward
      for (const code in diag.pull_forward) {
        const toSem = diag.pull_forward[code]
        buttons.push(<button key={buttons.length} className="autofix" onClick={() => {
          setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
            if (plan == null) return null
            return moveCourseByCode(plan, code, 0, toSem)
          })
        }}>
          Adelantar requisito  {getCourseName(reqCourses[code] ?? { code })}
        </button>)
      }
      // Add any absent requirements
      for (const code in diag.add_absent) {
        const onSem = diag.add_absent[code]
        buttons.push(<button key={buttons.length} className="autofix" onClick={() => {
          setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
            if (plan == null) return null
            const planArreglado = addCourseAt(plan, code, onSem)
            void getCourseDetails(planArreglado.classes.flat().filter(course => course.code === code))
            return planArreglado
          })
        }}>
          Agregar requisito {getCourseName(reqCourses[code] ?? { code })}
        </button>)
      }
      return (<>{buttons}</>)
    }
    case 'unknown':
      return <button className="autofix" onClick={() => {
        setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
          if (plan == null) return null
          const remCodes = new Set<string>()
          for (const id of diag.associated_to) {
            remCodes.add(id.code)
          }
          // Remove the referenced courses
          const newClasses = []
          for (const sem of plan.classes) {
            const newSem = []
            for (const course of sem) {
              if (!remCodes.has(course.code)) {
                newSem.push(course)
              }
            }
            newClasses.push(newSem)
          }
          return { ...plan, classes: newClasses }
        })
      }}>Eliminar cursos desconocidos</button>
    case 'equiv':
    case 'useless':
    case 'unavail':
    case 'sem':
    case 'nomajor':
    case 'currdecl':
    case 'creditserr':
    case 'creditswarn':
    case undefined:
      return <></>
  }
}

export default AutoFix
export { validateCyear }
