import { useState } from 'react'
import { FlatDiagnostic } from '../../client'
import { Spinner } from '../../components/Spinner'

/**
 * This is what is displayed when there are no errors or warnings.
 */
const NoMessages = ({ open }: { open: boolean }): JSX.Element => {
  return (
    <div className="flex p-3 mb-4 text-sm text-green-800 border border-green-300 rounded-lg bg-green-50 " role="alert">
      <svg aria-hidden="true" className="flex-shrink-0 inline-flex w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"></path></svg>
      <span className="sr-only">Info</span>
      <div className={`min-w-[14rem] ml-2 s${open ? '' : 'hidden'} `}>
        <span className='font-medium'>Felicitaciones!</span> No hay errores o advertencias.
      </div>
    </div>
  )
}

/**
 * A single error/warning message.
 */
const Message = (diag: FlatDiagnostic, key: number, open: boolean): JSX.Element => {
  const w = diag.is_warning

  return (
  <div key={key} className={`motion-reduce:transition-none transition-all  overflow-hidden flex p-3 text-sm rounded-lg border ${w ? 'text-yellow-700 border-yellow-300 bg-yellow-50' : 'text-red-800 border-red-300 bg-red-50'}`} role="alert">
    <svg aria-hidden="true" className="flex-shrink-0 inline-flex w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"></path></svg>
    <span className="sr-only">Info</span>
    <div className={`min-w-[14rem] ml-2 ${open ? '' : 'hidden'} `}>
      <span className={'font-semibold '}>{`${w ? 'Advertencia' : 'Error'}: `}</span>
      {`${diag.message}`}
    </div>
  </div>)
}

/**
 * The error tray shows errors and warnings about the current plan that come from the validation backend.
 */
const ErrorTray = ({ diagnostics, validating }: { diagnostics: FlatDiagnostic[], validating: boolean }): JSX.Element => {
  const [open, setOpen] = useState(true)
  const hasError = diagnostics.some(diag => !diag.is_warning)
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
  const messageList: JSX.Element[] = diagnostics.map((diag, index) => Message(diag, index, open || hasError))

  return (
      <div className={`h-[95%] z-20 flex flex-col relative border-slate-300 border-2 rounded-lg bg-slate-100 shadow-lg mb-2 overflow-y-auto overflow-x-hidden  py-4 px-3  motion-reduce:transition-none transition-all ${hasError || open ? 'w-80 min-w-[20rem]' : 'min-w-[4.5rem]'}`}>
        <div className='flex mb-4 mx-3'>
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
        <div className="flex flex-col gap-2 w-fit">
            {validating ? <Spinner message={`${hasError || open ? 'Validando...' : ''}`}/> : <>{messageList.length > 0 ? messageList : <NoMessages open={hasError || open}/>}</>}
        </div>
      </div>
  )
}

export default ErrorTray
