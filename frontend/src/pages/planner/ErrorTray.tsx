import { ClassId, CourseRequirementErr, CurriculumSpec, ValidationResult } from '../../client'
import { Spinner } from '../../components/Spinner'

type Diagnostic = ValidationResult['diagnostics'][number]
type RequirementExpr = CourseRequirementErr['missing']

/**
 * This is what is displayed when there are no errors or warnings.
 */
const NoMessages = (): JSX.Element => {
  return (<div className="flex p-4 mb-4 text-sm text-green-800 border border-green-300 rounded-lg bg-green-50 " role="alert">
  <svg aria-hidden="true" className="flex-shrink-0 inline w-5 h-5 mr-3" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"></path></svg>
  <span className="sr-only">Info</span>
  <div>
    <span className='font-medium'>Felicitaciones!</span> No hay errores o advertencias.
  </div>
</div>)
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
    case 'req':
      return `Faltan requisitos para el curso ${diag.associated_to[0]?.code}: ${formatReqExpr(diag.missing)}`
    case 'sem': {
      const sem = diag.only_available_on === 0 ? 'primeros' : diag.only_available_on === 1 ? 'segundos' : '?'
      const s = diag.associated_to.length !== 1
      return `${s ? 'El' : 'Los'} curso${s ? 's' : ''} ${listCourses(diag.associated_to)} solo se dictan los ${sem} semestres.`
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
      const s = diag.associated_to.length !== 1
      return `${diag.associated_to.length} curso${s ? 's' : ''} ${listCourses(diag.associated_to)} no cuenta${s ? 'n' : ''} para tu curriculum: ${listCourses(diag.associated_to)}`
    }
    case undefined:
      return '?'
  }
}

/**
 * A single error/warning message.
 */
const Message = (diag: Diagnostic, key: number): JSX.Element => {
  const w = !(diag.is_err ?? true)
  return (<div key={key} className={`flex p-3 text-sm rounded-lg border ${w ? 'text-yellow-700 border-yellow-300 bg-yellow-50' : 'text-red-800 border-red-300 bg-red-50'}`} role="alert">
  <svg aria-hidden="true" className="flex-shrink-0 inline w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"></path></svg>
  <span className="sr-only">Info</span>
  <div>
    <span className="font-semibold">{`${w ? 'Advertencia' : 'Error'}: `}</span> {formatMessage(diag)}
  </div>
</div>)
}

/**
 * The error tray shows errors and warnings about the current plan that come from the validation backend.
 */
const ErrorTray = ({ diagnostics, validating }: { diagnostics: Diagnostic[], validating: boolean }): JSX.Element => {
  // Order diagnostics by putting errors first, then warnings.
  diagnostics.sort((a, b) => {
    if (a.is_err === b.is_err) {
      return 0
    } else if (a.is_err ?? true) {
      return -1
    } else {
      return 1
    }
  })
  const messageList: JSX.Element[] = diagnostics.map((diag, index) => Message(diag, index))
  return (<div className="w-80 min-w-[200px] h-[95%] mb-6 overflow-y-auto px-5 py-6 bg-slate-100 border-slate-300 border-2 rounded-lg shadow-lg">
    <p className="text-xl font-semibold mb-4 text-center">Errores y advertencias</p>
  <div className="flex flex-col gap-2">
    {validating ? <Spinner message='Validando...'/> : <>{messageList.length > 0 ? messageList : <NoMessages/>}</>}
  </div>
  </div>)
}

export default ErrorTray
