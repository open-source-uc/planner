import { useEffect, useRef, useState } from 'react'
import { type ClassId, type CurriculumSpec } from '../../client'
import { type PseudoCourseDetail, isCourseRequirementErr, type RequirementExpr, type Diagnostic } from './utils/Types'
import { Spinner } from '../../components/Spinner'
import AutoFix from './utils/AutoFix'
import { collectRequirements, getCourseName, getCourseNameWithCode } from './utils/utils'
import { validateCyear } from './utils/planBoardFunctions'
import { useConfetti } from '../../contexts/confetti.context'

/**
 * This is what is displayed when there are no errors or warnings.
 */
const NoMessages = ({ open }: { open: boolean }): JSX.Element => {
  return (
    <div className="w-fit flex p-3 mb-4 text-sm text-green-800 border border-green-300 rounded-lg bg-green-50 " role="alert">
      🎉
      <span className="sr-only">Info</span>
      <div className={`min-w-[14rem] ml-2 ${open ? '' : 'hidden'} `}>
        <span className='font-medium'>Felicitaciones!</span> No hay errores o advertencias.
      </div>
    </div>
  )
}

interface FormattedRequirementProps {
  expr: RequirementExpr
  reqCourses: Record<string, PseudoCourseDetail | string>
}

export const FormattedRequirement: React.FC<FormattedRequirementProps> = ({ expr, reqCourses }) => {
  switch (expr.expr) {
    case 'and': case 'or':
      return (
        <span>
          {expr.children.map((subexpr, index) => {
            const subexprComponent = subexpr.expr === 'and' || subexpr.expr === 'or'
              ? <span>({<FormattedRequirement expr={subexpr} reqCourses={reqCourses} />})</span>
              : <FormattedRequirement expr={subexpr} reqCourses={reqCourses} />

            return index !== expr.children.length - 1
              ? <span key={index}>{subexprComponent} {expr.expr === 'and' ? 'y' : 'o'} </span>
              : subexprComponent
          })}
        </span>
      )
    case 'const':
      return <span>{expr.value ? 'true' : 'false'}</span>
    case 'cred':
      return <span>Créditos &gt;= {expr.min_credits}</span>
    case 'lvl':
      return <span>Nivel {expr.equal ? '=' : '!='} {expr.level}</span>
    case 'school':
      return <span>Facultad {expr.equal ? '=' : '!='} {expr.school}</span>
    case 'program':
      return <span>Programa {expr.equal ? '=' : '!='} {expr.program}</span>
    case 'career':
      return <span>Carrera {expr.equal ? '=' : '!='} {expr.career}</span>
    case 'req':
      return <span><CourseName course={reqCourses[expr.code] ?? expr.code } />{expr.coreq ? ' (c)' : ''}</span>
    case undefined:
      return <span>?</span>
  }
}

export const CourseName = ({ course }: { course: string | ClassId | PseudoCourseDetail }): JSX.Element => {
  // This component version uses a ruby to show the course code
  // This is useful to disambiguate courses with the same name
  // (e.g. "Proyecto de Título")
  const name = getCourseName(course)
  const code = typeof course === 'string' ? course : course.code
  if (name != null) {
    return (
      <abbr title={code}>
        {name}
      </abbr>
    )
  } else {
    return (
      <span>
        {code}
      </span>
    )
  }
}

/**
 * Format a list of courses as a human readable list of codes.
 */
const listCourses = (courses: Array<ClassId | PseudoCourseDetail>): string => {
  const courseNames: string[] = courses.map(c => (
    getCourseNameWithCode(c)
  ))
  if (courseNames.length > 1) return `${courseNames.slice(0, -1).join(', ')} y ${courseNames[courseNames.length - 1]}`
  else if (courseNames.length === 1) return courseNames[0]
  else return '()'
}

/**
 * Format a curriculum specification.
 */
const formatCurriculum = (curr: CurriculumSpec): string => {
  const pieces: string[] = []
  if (curr.major != null) pieces.push(curr.major)
  if (curr.minor != null) pieces.push(curr.minor)
  if (curr.title != null) pieces.push(curr.title)
  return pieces.length === 0 ? '-' : pieces.join('-')
}

interface FormatMessageProps {
  diag: Diagnostic
  reqCourses: Record<string, PseudoCourseDetail | string>
}

export const ValidationMessage: React.FC<FormatMessageProps> = ({ diag, reqCourses }) => {
  switch (diag.kind) {
    case 'credits': {
      const sem: number = diag.associated_to[0]
      if (diag.is_err) {
        return <span>Tienes {diag.actual} créditos en el semestre {sem + 1}, más de los {diag.credit_limit} que se permiten tomar en un semestre.</span>
      } else {
        return <span>Tienes {diag.actual} créditos en el semestre {sem + 1}, revisa que cumplas los requisitos para tomar más de {diag.credit_limit} créditos.</span>
      }
    }
    case 'curr': {
      const n = diag.blocks.length
      return <span>Faltan {diag.credits} créditos {n === 1 ? 'para el bloque' : 'entre los bloques'} {diag.blocks.map(path => path.join(' -> ')).join(', ')}.</span>
    }
    case 'currdecl':
      return <span>El curriculum elegido ({formatCurriculum(diag.plan)}) es distinto al que tienes declarado oficialmente ({formatCurriculum(diag.user)}).</span>
    case 'cyear':
      if (validateCyear(diag.user) != null) {
        return <span>Tu versión de curriculum es {diag.user}, pero el plan esta siendo validado para {diag.plan}.</span>
      } else {
        return <span>Tu versión del curriculum es {diag.user} pero no es soportada. El plan esta siendo validado para la versión de curriculum {diag.plan}.</span>
      }
    case 'equiv': {
      const n = diag.associated_to.length
      return <span>Falta especificar {n} equivalencia{n === 1 ? '' : 's'} para validar correctamente tu plan.</span>
    }
    case 'nomajor': {
      let missing = ''
      if (diag.plan.major == null) missing += 'un major'
      if (diag.plan.minor == null) {
        if (missing !== '') missing += ' y '
        missing += 'un minor'
      }
      return <span>Debes seleccionar {missing} para validar correctamente tu plan.</span>
    }
    case 'outdated':
      if (diag.is_current === true) {
        return <span>Esta malla no está actualizada con los cursos que estás tomando.</span>
      } else {
        return <span>Esta malla no está actualizada con los cursos que has tomado.</span>
      }
    case 'recolor': {
      const n = diag.associated_to.length
      if (diag.is_err) {
        return <span>Debes reasignar {n} curso{n === 1 ? '' : 's'} para satisfacer tu currículum.</span>
      } else {
        return <span>Puedes reasignar {n} curso{n === 1 ? '' : 's'} para ahorrarte créditos.</span>
      }
    }
    case 'req':
      return <span>Faltan requisitos para el curso <CourseName course={diag.associated_to[0]} />: <FormattedRequirement expr={diag.modernized_missing} reqCourses={reqCourses}/></span>
    case 'sem': {
      const sem = diag.only_available_on === 0 ? 'impares' : diag.only_available_on === 1 ? 'pares' : '?'
      const s = diag.associated_to.length !== 1
      return <span>{s ? 'Los' : 'El'} curso{s ? 's' : ''} {listCourses(diag.associated_to)} solo se dicta{s ? 'n' : ''} los semestres {sem}.</span>
    }
    case 'unavail': {
      const s = diag.associated_to.length !== 1
      return <span>{s ? 'Los' : 'El'} curso{s ? 's' : ''} {listCourses(diag.associated_to)} no se ha{s ? 'n' : ''} dictado en mucho tiempo y posiblemente no se siga{s ? 'n' : ''} dictando.</span>
    }
    case 'unknown': {
      const s = diag.associated_to.length !== 1 ? 's' : ''
      return <span>Código{s} de curso desconocido{s}: {listCourses(diag.associated_to)}</span>
    }
    case 'useless': {
      const creds: number = diag.unassigned_credits
      return <span>Tienes {creds} cŕeditos que no cuentan para tu curriculum.</span>
    }
    case undefined:
      return <span>?</span>
    default:
      // unreachable
      return diag
  }
}

interface MessageProps {
  setValidatablePlan: any
  getCourseDetails: Function
  diag: Diagnostic
  key: number
  open: boolean
  reqCourses: any
}

/**
 * A single error/warning message.
 */
const Message = ({ setValidatablePlan, getCourseDetails, reqCourses, diag, key, open }: MessageProps): JSX.Element => {
  const w = !(diag.is_err ?? true)

  return (
  <div key={key} className={`w-fit flex py-3 px-2 text-sm rounded-lg border ${w ? 'text-yellow-700 border-yellow-300 bg-yellow-50' : 'text-red-800 border-red-300 bg-red-50'}`} role="alert">
    <svg aria-hidden="true" className="flex-shrink-0 inline-flex w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"></path></svg>
    <span className="sr-only">Info</span>
    <div className={open ? '' : 'hidden'}>
      <div className={'min-w-[14rem] ml-2 mb-3'}>
        <span className={'font-semibold '}>{`${w ? 'Advertencia' : 'Error'}: `}</span>
        <ValidationMessage diag={diag} reqCourses={reqCourses}/>
      </div>
      <AutoFix setValidatablePlan={setValidatablePlan} getCourseDetails={getCourseDetails} reqCourses={reqCourses} diag={diag}/>
    </div>
  </div>
  )
}

interface ErrorTrayProps {
  setValidatablePlan: any
  getCourseDetails: Function
  diagnostics: Diagnostic[]
  validating: boolean
  courseDetails: Record<string, PseudoCourseDetail>
}

/**
 * The error tray shows errors and warnings about the current plan that come from the validation backend.
 */
const ErrorTray = ({ setValidatablePlan, diagnostics, validating, courseDetails, getCourseDetails }: ErrorTrayProps): JSX.Element => {
  const [open, setOpen] = useState(true)
  const hasError = diagnostics.some(diag => diag.is_err)

  const messageList: JSX.Element[] = diagnostics.map((diag, index) => {
    const reqCourses: Record<string, PseudoCourseDetail | string> = {}
    if (isCourseRequirementErr(diag)) {
      const reqCodes = new Set<string>()
      collectRequirements(diag.modernized_missing, reqCodes)
      for (const code of reqCodes) {
        reqCourses[code] = courseDetails[code] ?? code
      }
    }
    return Message({ setValidatablePlan, diag, key: index, open: open || hasError, getCourseDetails, reqCourses })
  })

  // Determine when we get 0 messages to launch the confetti
  const hadErrorsRef = useRef(false)
  const hasErrors = messageList.length > 0
  const confetti = useConfetti()
  useEffect(() => {
    if (hadErrorsRef.current && !hasErrors) {
      if (confetti != null) {
        void confetti.addConfetti({
          emojis: ['🌈', '⚡️', '💥', '✨', '💫'],
          emojiSize: 70
        })
      }
    }
    hadErrorsRef.current = hasErrors
  }, [hasErrors, confetti])

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
          <button className={`${hasError ? 'cursor-not-allowed stroke-slate-400' : 'stroke-current'}`} disabled={hasError} onClick={() => { setOpen(prev => !prev) }}>
            <svg className="w-5 h-5 flex " xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M2 12h20M2 6h20M2 18h20"></path>
            </svg>
          </button>
        </div>
        {(hasError || open) && <p className="whitespace-nowrap ml-2 text-xl font-semibold text-center h-7 overflow-hidden">Errores y Advertencias </p>}
      </div>
      <div className="h-full flex flex-col gap-2 px-3 overflow-y-auto overflow-x-hidden ">
          {validating ? <div> <Spinner message={`${hasError || open ? 'Validando...' : ''}`}/></div> : <>{messageList.length > 0 ? messageList : <NoMessages open={open}/>}</>}
      </div>
    </div>
  )
}

export default ErrorTray
