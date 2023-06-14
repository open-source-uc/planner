import { useState } from 'react'
import { ClassId, CourseRequirementErr, CurriculumSpec, ValidatablePlan, ValidationResult } from '../../client'
import { Spinner } from '../../components/Spinner'
import { useAuth } from '../../contexts/auth.context'

type Diagnostic = ValidationResult['diagnostics'][number]
type RequirementExpr = CourseRequirementErr['missing']

/**
 * This is what is displayed when there are no errors or warnings.
 */
const NoMessages = ({ open }: { open: boolean }): JSX.Element => {
  return (
    <div className="w-fit flex p-3 mb-4 text-sm text-green-800 border border-green-300 rounded-lg bg-green-50 " role="alert">
      <svg aria-hidden="true" className="flex-shrink-0 inline-flex w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"></path></svg>
      <span className="sr-only">Info</span>
      <div className={`min-w-[14rem] ml-2 s${open ? '' : 'hidden'} `}>
        <span className='font-medium'>Felicitaciones!</span> No hay errores o advertencias.
      </div>
    </div>
  )
}

/**
 * Format a course requirement expression.
 */
const formatReqExpr = (expr: RequirementExpr): string => {
  // Este switch gigante esta chequeado por typescript
  // Si no se chequean exactamente todas las opciones tira error
  switch (expr.expr) {
    case 'and': case 'or':
      return expr.children.map(subexpr => {
        if (subexpr.expr === 'and' || subexpr.expr === 'or') return `(${formatReqExpr(subexpr)})`
        else return formatReqExpr(subexpr)
      }).join(expr.expr === 'and' ? ' y ' : ' o ')
    case 'const':
      return expr.value ? 'true' : 'false'
    case 'cred':
      return `Créditos >= ${expr.min_credits}`
    case 'lvl':
      return `Nivel = ${expr.min_level}`
    case 'school':
      return `Facultad ${expr.equal ? '=' : '!='} ${expr.school}`
    case 'program':
      return `Programa ${expr.equal ? '=' : '!='} ${expr.program}`
    case 'career':
      return `Carrera ${expr.equal ? '=' : '!='} ${expr.career}`
    case 'req':
      return `${expr.code}${expr.coreq ? '(c)' : ''}`
    case undefined:
      return '?'
  }
}

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

/**
 * Format a list of courses as a human readable list of codes.
 */
const listCourses = (courses: ClassId[]): string => {
  const a = courses.map(c => c.code)
  if (a.length > 1) return `${a.slice(0, -1).join(', ')} y ${a[a.length - 1]}`
  else if (a.length === 1) return a[0]
  else return '()'
}

/**
 * Format a curriculum specification.
 */
const formatCurriculum = (curr: CurriculumSpec): string => {
  const major: string = curr.major ?? '()'
  const minor: string = curr.minor ?? '()'
  const title: string = curr.title ?? '()'
  return `${major}-${minor}-${title}`
}

/**
 * Get the error message for a given diagnostic.
 */
const formatMessage = (diag: Diagnostic): string => {
  // Este switch gigante esta chequeado por typescript
  // Si no se chequean exactamente todas las opciones tira error
  switch (diag.kind) {
    case 'creditserr':
      return `Tienes ${diag.actual} créditos en el semestre ${diag.associated_to[0] + 1}, más de los ${diag.max_allowed} que se permiten tomar en un semestre.`
    case 'creditswarn':
      return `Tienes ${diag.actual} créditos en el semestre ${diag.associated_to[0] + 1}, revisa que cumplas los requisitos para tomar más de ${diag.max_recommended} créditos.`
    case 'curr':
      return `Faltan ${diag.credits} créditos para el bloque ${diag.block}`
    case 'currdecl':
      return `El curriculum elegido (${formatCurriculum(diag.plan)}) no es el mismo que el que tienes declarado oficialmente (${formatCurriculum(diag.user)})`
    case 'cyear':
      return `Tu versión de curriculum es ${diag.user}, pero el plan esta siendo validado para ${diag.plan.raw}.`
    case 'equiv': {
      const s = diag.associated_to.length === 1 ? '' : 's'
      return `Falta desambiguar la${s} equivalencia${s} ${listCourses(diag.associated_to)} para validar correctamente tu plan.`
    }
    case 'nomajor': {
      let missing = ''
      if (diag.plan.major == null) missing += 'un major'
      if (diag.plan.minor == null) {
        if (missing !== '') missing += ' y '
        missing += 'un minor'
      }
      return `Debes seleccionar ${missing} para validar correctamente tu plan.`
    }
    case 'outdated':
      return 'Esta malla no está actualizada con los cursos que has tomado'
    case 'outdatedcurrent':
      return 'Esta malla no está actualizada con los cursos que estás tomando'
    case 'req':
      return `Faltan requisitos para el curso ${diag.associated_to[0]?.code}: ${formatReqExpr(diag.missing)}`
    case 'sem': {
      const sem = diag.only_available_on === 0 ? 'primeros' : diag.only_available_on === 1 ? 'segundos' : '?'
      const s = diag.associated_to.length !== 1
      return `${s ? 'Los' : 'El'} curso${s ? 's' : ''} ${listCourses(diag.associated_to)} solo se dicta${s ? 'n' : ''} los ${sem} semestres.`
    }
    case 'unavail': {
      const s = diag.associated_to.length !== 1
      return `${s ? 'Los' : 'El'} curso${s ? 's' : ''} ${listCourses(diag.associated_to)} no se ha${s ? 'n' : ''} dictado en mucho tiempo y probablemente no se siga${s ? 'n' : ''} dictando.`
    }
    case 'unknown': {
      const s = diag.associated_to.length !== 1 ? 's' : ''
      return `Código${s} de curso desconocido${s}: ${listCourses(diag.associated_to)}`
    }
    case 'useless': {
      const creds: number = diag.unassigned_credits
      return `Tienes ${creds} cŕeditos que no cuentan para tu curriculum.`
    }
    case undefined:
      return '?'
  }
}

/**
 * Get the quick fixed for some diagnostic, if any.
 */
const QuickFixes = ({ diag, setValidatablePlan }: { diag: Diagnostic, setValidatablePlan: any }): JSX.Element => {
  const auth = useAuth()
  switch (diag.kind) {
    case 'curr':
      return <button onClick={() => {
        setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
          if (plan == null) return null
          // Add the recommended courses to the last semester
          const newClasses = [...plan.classes]
          const semIdx = newClasses.length - 1
          newClasses[semIdx] = [...newClasses[semIdx]]
          for (const recommendation of diag.recommend) {
            newClasses[semIdx].push(recommendation)
          }
          return { ...plan, classes: newClasses }
        })
      }}>Agregar {diag.recommend.map(c => c.code).join(', ')}</button>
    case 'cyear':
      return <button onClick={() => {
        setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
          if (plan == null) return null
          if (diag.user === 'C2020') {
            return { ...plan, curriculum: { ...plan.curriculum, cyear: { raw: diag.user } } }
          } else {
            return plan
          }
        })
      }}>Cambiar a {diag.user}</button>
    case 'outdated':
    case 'outdatedcurrent':
      if (auth != null) {
        return <button onClick={() => {
          setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
            if (plan == null) return null
            // Update all outdated semesters
            const newClasses = [...plan.classes]
            for (const semIdx of diag.associated_to) {
              const passedSem = auth.student?.passed_courses?.[semIdx]
              if (passedSem != null) {
                newClasses[semIdx] = passedSem
              }
            }
            return { ...plan, classes: newClasses }
          })
        }}>Actualizar semestres {diag.associated_to.map(s => s + 1).join(', ')}</button>
      } else {
        return <></>
      }
    case 'req': {
      const missing = extractRequiredCourses(diag.missing)
      const buttons = []
      for (const code in missing) {
        const type = missing[code]
        buttons.push(<button onClick={() => {
          setValidatablePlan((plan: ValidatablePlan | null): ValidatablePlan | null => {
            if (plan == null) return null
            // Add the missing requirement
            const newClasses = [...plan.classes]
            const semIdx = newClasses.length - 1
            newClasses[semIdx] = [...newClasses[semIdx]]
            newClasses[semIdx].push({
              is_concrete: true,
              code
            })
            return { ...plan, classes: newClasses }
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

interface MessageProps {
  setValidatablePlan: any
  diag: Diagnostic
  key: number
  open: boolean
}

/**
 * A single error/warning message.
 */
const Message = ({ setValidatablePlan, diag, key, open }: MessageProps): JSX.Element => {
  const w = !(diag.is_err ?? true)

  return (
  <div key={key} className={`w-fit flex p-3 text-sm rounded-lg border ${w ? 'text-yellow-700 border-yellow-300 bg-yellow-50' : 'text-red-800 border-red-300 bg-red-50'}`} role="alert">
    <svg aria-hidden="true" className="flex-shrink-0 inline-flex w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"></path></svg>
    <span className="sr-only">Info</span>
    <div className={`min-w-[14rem] ml-2 ${open ? '' : 'hidden'} `}>
      <span className={'font-semibold '}>{`${w ? 'Advertencia' : 'Error'}: `}</span>
      {formatMessage(diag)}
      <QuickFixes setValidatablePlan={setValidatablePlan} diag={diag}/>
    </div>
  </div>)
}

interface ErrorTrayProps {
  setValidatablePlan: any
  diagnostics: Diagnostic[]
  validating: boolean
}

/**
 * The error tray shows errors and warnings about the current plan that come from the validation backend.
 */
const ErrorTray = ({ setValidatablePlan, diagnostics, validating }: ErrorTrayProps): JSX.Element => {
  const [open, setOpen] = useState(true)
  const hasError = diagnostics.some(diag => diag.is_err)
  // Order diagnostics by putting errors first, then warnings.
  // FIXME: Move this to the validation endpoint
  diagnostics.sort((a, b) => {
    if (a.is_err === b.is_err) {
      return 0
    } else if (a.is_err ?? true) {
      return -1
    } else {
      return 1
    }
  })
  const messageList: JSX.Element[] = diagnostics.map((diag, index) => Message({ setValidatablePlan, diag, key: index, open: open || hasError }))
  return (
    <div className={`h-[95%] z-20 flex flex-col relative border-slate-300 border-2 rounded-lg bg-slate-100 shadow-lg mb-2 py-4  motion-reduce:transition-none transition-all ${hasError || open ? 'w-80 min-w-[20rem]' : 'min-w-[4.5rem]'}`}>
      <div className='flex mb-4 mx-6'>
        <div className='group relative flex'>
          <span className={`fixed z-10 transition-all motion-reduce:transition-none scale-0 ${hasError ? 'group-hover:scale-100' : ''}`}>
            <div className="absolute right-2.5 top-1 w-4 h-4 bg-gray-800 rotate-45 rounded" />
            <span className={'absolute right-4 -top-1 w-48 z-10 rounded bg-gray-800 p-2 text-xs text-white'}>
              Es necesario resolver todos los errores existentes para minimizar la bandeja de Errores y Advertencias.
            </span>
          </span>
          <button className={`${hasError ? 'cursor-not-allowed stroke-slate-400' : 'stroke-current'}`} disabled={hasError} onClick={() => setOpen(prev => !prev)}>
            <svg className="w-5 h-5 flex " xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M2 12h20M2 6h20M2 18h20"></path>
            </svg>
          </button>
        </div>
        {(hasError || open) && <p className="whitespace-nowrap ml-2 text-xl font-semibold text-center h-7 overflow-hidden">Errores y Advertencias </p>}
      </div>
      <div className="h-full flex flex-col gap-2 px-3 overflow-y-auto overflow-x-hidden ">
          {validating ? <div> <Spinner message={`${hasError || open ? 'Validando...' : ''}`}/></div> : <>{messageList.length > 0 ? messageList : <NoMessages open={hasError || open}/>}</>}
      </div>
    </div>
  )
}

export default ErrorTray
