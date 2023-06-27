import { type CourseRequirementErr, type CurriculumErr, type Cyear, type MismatchedCyearErr, type OutdatedCurrentSemesterErr, type OutdatedPlanErr, type ValidatablePlan, type ValidationResult } from '../../../client'
import { type AuthState, useAuth } from '../../../contexts/auth.context'

type Diagnostic = ValidationResult['diagnostics'][number]
type RequirementExpr = CourseRequirementErr['missing']

const extractRequiredCourses = (expr: RequirementExpr, out: Record<string, 'req' | 'coreq'> = {}): Record<string, 'req' | 'coreq'> => {
  switch (expr.expr) {
    case 'req':
      out[expr.code] = expr.coreq ? 'coreq' : 'req'
      break
    case 'and':
    case 'or':
      for (const sub of expr.children) {
        extractRequiredCourses(sub, out)
      }
  }
  return out
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

const fixMissingCurriculumCourse = (plan: ValidatablePlan, diag: CurriculumErr, auth: AuthState | null): ValidatablePlan => {
  // Add the recommended courses to wherever there's fewer courses
  const nextSemester = auth?.student?.next_semester ?? 0
  const newClasses = [...plan.classes]
  while (newClasses.length <= nextSemester) newClasses.push([])
  for (const recommendation of diag.recommend) {
    const semIdx = findSemesterWithLeastCourses(newClasses, auth, null)
    // Add the recommended course to this semester
    newClasses[semIdx] = [...newClasses[semIdx]]
    newClasses[semIdx].push(recommendation)
  }
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

const fixMissingRequirement = (plan: ValidatablePlan, diag: CourseRequirementErr, auth: AuthState | null, missingCode: string, reqType: 'req' | 'coreq'): ValidatablePlan => {
  // Find where is the diagnostic course (ie. the course that is missing a `missingCode` requirement)
  if (diag.associated_to.length === 0) return plan
  const mainCourse = diag.associated_to[0]
  let mainCourseSem: number | null = null
  {
    let k = 0
    for (let i = 0; i < plan.classes.length; i++) {
      const sem = plan.classes[i]
      for (let j = 0; j < sem.length; j++) {
        if (sem[j].code === mainCourse.code) {
          if (k === mainCourse.instance) {
            mainCourseSem = i
          }
          k += 1
        }
      }
    }
  }
  if (mainCourseSem == null) return plan
  // Add the missing requirement in the semester with the least amount of courses
  const newClasses = [...plan.classes]
  const semIdx = findSemesterWithLeastCourses(newClasses, auth, mainCourseSem + (reqType === 'coreq' ? 1 : 0))
  newClasses[semIdx] = [...newClasses[semIdx]]
  newClasses[semIdx].push({
    is_concrete: true,
    code: missingCode
  })
  return { ...plan, classes: newClasses }
}

/**
 * Get the quick fixed for some diagnostic, if any.
 */
const AutoFix = ({ diag, setValidatablePlan }: { diag: Diagnostic, setValidatablePlan: any }): JSX.Element => {
  // FIXME: TODO: Los cursos añadidos a traves del autofix les faltan los CourseDetails.
  // No me manejo bien con la implementación del frontend, lo dejo en mejores manos.
  const auth = useAuth()
  switch (diag.kind) {
    case 'curr':
      return <button onClick={() => {
        setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
          if (plan == null) return null
          return fixMissingCurriculumCourse(plan, diag, auth)
        })
      }}>Agregar {diag.recommend.map(c => c.code).join(', ')}</button>
    case 'cyear':
      if (validateCyear(diag.user) != null) {
        return <button onClick={() => {
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
        return <button onClick={() => {
          setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
            if (plan == null) return null
            return fixOutdatedPlan(plan, diag, auth)
          })
        }}>Actualizar semestres {diag.associated_to.map(s => s + 1).join(', ')}</button>
      } else {
        return <></>
      }
    case 'req': {
      const missing = extractRequiredCourses(diag.modernized_missing)
      const buttons = []
      for (const code in missing) {
        const type = missing[code]
        buttons.push(<button key={code} onClick={() => {
          setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
            if (plan == null) return null
            return fixMissingRequirement(plan, diag, auth, code, type)
          })
        }}>
            Agregar {type === 'req' ? 'requisito' : 'corequisito'} {code}
          </button>)
      }
      return <>
          {buttons}
        </>
    }
    case 'unknown':
      return <button onClick={() => {
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
