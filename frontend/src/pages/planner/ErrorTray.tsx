import { FlatDiagnostic } from '../../client'
import { Spinner } from '../../components/Spinner'

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
 * A single error/warning message.
 */
const Message = (diag: FlatDiagnostic, key: number): JSX.Element => {
  const w = diag.is_warning
  const coursePrefix = diag.course_code == null ? '' : `${diag.course_code}: `
  return (<div key={key} className={`flex p-4 text-sm rounded-lg border ${w ? 'text-yellow-700 border-yellow-300 bg-yellow-50' : 'text-red-800 border-red-300 bg-red-50'}`} role="alert">
  <svg aria-hidden="true" className="flex-shrink-0 inline w-5 h-5 mr-3" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"></path></svg>
  <span className="sr-only">Info</span>
  <div>
    <span className="font-semibold">{`${w ? 'Advertencia' : 'Error'}: `}</span> {`${coursePrefix}${diag.message}`}
  </div>
</div>)
}

/**
 * The error tray shows errors and warnings about the current plan that come from the validation backend.
 */
const ErrorTray = ({ diagnostics, validating }: { diagnostics: FlatDiagnostic[], validating: boolean }): JSX.Element => {
  // Order diagnostics by putting errors first, then warnings.
  diagnostics.sort((a, b) => {
    if (a.is_warning === b.is_warning) {
      return 0
    } else if (a.is_warning) {
      return 1
    } else {
      return -1
    }
  })
  const messageList: JSX.Element[] = diagnostics.map((diag, index) => Message(diag, index))
  return (<div className="w-80 h-[95%] mb-6 overflow-y-auto px-5 py-6 bg-slate-100 border-slate-300 border-2 rounded-lg shadow-lg">
    <p className="text-xl font-semibold mb-4 text-center">Errores y advertencias</p>
  <div className="flex flex-col gap-2">
    {validating ? <Spinner message='Validando...'/> : <>{messageList.length > 0 ? messageList : <NoMessages/>}</>}
  </div>
  </div>)
}

export default ErrorTray
