import { useEffect, useRef, useState } from 'react'
import { type ClassId, type CourseRequirementErr, type CurriculumSpec, type ValidationResult } from '../../client'
import { type PseudoCourseDetail, isCourseRequirementErr, isDiagWithAssociatedCourses } from './utils/Types'
import { Spinner } from '../../components/Spinner'
import AutoFix from './utils/AutoFix'
import { collectRequirements, getCourseName, getCourseNameWithCode } from './utils/utils'
import { validateCyear } from './utils/planBoardFunctions'
import { useConfetti } from '../../contexts/confetti.context'

type Diagnostic = ValidationResult['diagnostics'][number]
type RequirementExpr = CourseRequirementErr['missing']
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
  reqCourses: any
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
              ? <span>{subexprComponent} {expr.expr === 'and' ? 'y' : 'o'} </span>
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
      return <span><CourseName course={reqCourses[expr.code] ?? { code: expr.code }} />{expr.coreq ? ' (c)' : ''}</span>
    case undefined:
      return <span>?</span>
  }
}

export const CourseName = ({ course }: { course: ClassId | PseudoCourseDetail }): JSX.Element => {
  // This component version uses a ruby to show the course code
  // This is useful to disambiguate courses with the same name
  // (e.g. "Proyecto de Título")
  const name = getCourseName(course)
  if (name != null) {
    return (
      <abbr title={course.code}>
        {name}
      </abbr>
    )
  } else {
    return (
      <span>
        {course.code}
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
  reqCourses: any
}

export const MessageText: React.FC<FormatMessageProps> = ({ diag, reqCourses }) => {
  switch (diag.kind) {
    case 'creditserr':
      return <span>Tienes {diag.actual} créditos en el semestre {diag.associated_to[0] + 1}, más de los {diag.max_allowed} que se permiten tomar en un semestre.</span>
    case 'creditswarn':
      return <span>Tienes {diag.actual} créditos en el semestre {diag.associated_to[0] + 1}, revisa que cumplas los requisitos para tomar más de {diag.max_recommended} créditos.</span>
    case 'curr': {
      const n = diag.blocks.length
      return <span>Faltan {diag.credits} créditos {n === 1 ? 'para el bloque' : 'entre los bloques'} {diag.blocks.map(path => path.join(' -> ')).join(', ')}.</span>
    }
    case 'currdecl':
      return <span>El curriculum elegido ({formatCurriculum(diag.plan)}) es distinto al que tienes declarado oficialmente ({formatCurriculum(diag.user)}).</span>
    case 'cyear':
      if (validateCyear(diag.user) != null) {
        return <span>Tu versión de curriculum es {diag.user}, pero el plan esta siendo validado para {diag.plan.raw}.</span>
      } else {
        return <span>Tu versión del curriculum es {diag.user} pero no es soportada. El plan esta siendo validado para la versión de curriculum {diag.plan.raw}.</span>
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
      return <span>Esta malla no está actualizada con los cursos que has tomado.</span>
    case 'outdatedcurrent':
      return <span>Esta malla no está actualizada con los cursos que estás tomando.</span>
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
const MessageBox = ({ setValidatablePlan, getCourseDetails, reqCourses, diag, key, open }: MessageProps): JSX.Element => {
  const w = !(diag.is_err ?? true)

  return (
  <div key={key} className={`w-fit flex py-3 px-2 text-sm rounded-lg border ${w ? 'text-yellow-700 border-yellow-300 bg-yellow-50' : 'text-red-800 border-red-300 bg-red-50'}`} role="alert">
    <svg aria-hidden="true" className="flex-shrink-0 inline-flex w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"></path></svg>
    <span className="sr-only">Info</span>
    <div className={open ? '' : 'hidden'}>
      <div className={'min-w-[14rem] ml-2 mb-3'}>
        <span className={'font-semibold '}>{`${w ? 'Advertencia' : 'Error'}: `}</span>
        <MessageText diag={diag} reqCourses={reqCourses}/>
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
  courseDetails: any
}

/**
 * The error tray shows errors and warnings about the current plan that come from the validation backend.
 */
const ErrorTray = ({ setValidatablePlan, diagnostics, validating, courseDetails, getCourseDetails }: ErrorTrayProps): JSX.Element => {
  const [open, setOpen] = useState(true)
  const hasError = diagnostics.some(diag => diag.is_err)

  const messageList: JSX.Element[] = diagnostics.map((diag, index) => {
    let diagWithAssociated = diag
    const reqCourses: any = {}
    if (isDiagWithAssociatedCourses(diag)) diagWithAssociated = { ...diag, associated_to: diag.associated_to.map((course: ClassId) => courseDetails[course.code] !== undefined ? { ...courseDetails[course.code], instance: course.instance } : { code: course.code }) }
    if (isCourseRequirementErr(diag)) {
      const reqCodes = new Set<string>()
      collectRequirements(diag.modernized_missing, reqCodes)
      for (const code of reqCodes) {
        reqCourses[code] = courseDetails[code] ?? code
      }
    }
    return MessageBox({ setValidatablePlan, diag: diagWithAssociated, key: index, open: open || hasError, getCourseDetails, reqCourses })
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
    <div className={`h-fit max-h-[80%] z-20 flex flex-col absolute top-4 right-4 border-slate-300 border-2 rounded-lg bg-slate-100 shadow-lg mb-2 py-4  motion-reduce:transition-none transition-all ${hasError || open ? 'w-80 min-w-[20rem]' : 'min-w-[4.5rem]'}`}>
      {/* Open/close + (optional) Title */}
      <div className='flex mb-4 mx-6'>
        {/* Open/close tray button */}
        <div className='group relative flex'>
          <button className="stroke-current" onClick={() => { setOpen(prev => !prev) }}>
            <svg className="w-4 h-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M2 12h20M2 6h20M2 18h20"></path>
            </svg>
          </button>
        </div>
        {/* Title */}
        {(hasError || open) && <p className="whitespace-nowrap ml-2 text-lg font-semibold text-center h-7 overflow-hidden">Errores y Advertencias </p>}
      </div>
      {/* The tray itself */}
      <div className="h-full flex flex-col gap-2 px-3 overflow-y-auto overflow-x-hidden ">
          {validating ? <div> <Spinner message={`${hasError || open ? 'Validando...' : ''}`}/></div> : <>{messageList.length > 0 ? messageList : <NoMessages open={open}/>}</>}
      </div>
    </div>
  )
}

export default ErrorTray
