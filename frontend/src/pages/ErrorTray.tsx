
import errorIcon from '../assets/error.svg'
import warningIcon from '../assets/warning.svg'
import okIcon from '../assets/ok.svg'
import { Diagnostic } from '../client'

const NoMessages = (): JSX.Element => {
  return (<div className="flex flex-col items-center">
    <img className="w-10 h-10" src={okIcon} alt="No hay errores" />
    <p className="font-light">Todo OK!</p>
  </div>)
}

const Message = (diag: Diagnostic): JSX.Element => {
  const w = diag.is_warning
  const coursePrefix = diag.course_code === undefined ? '' : `${diag.course_code}: `
  return (<div className={'flex flex-row items-center gap-4 ' + (w ? 'font-normal' : 'font-medium')}>
    <img
      className="w-12 h-12"
      src={w ? warningIcon : errorIcon}
      alt={w ? 'Warning' : 'Error'}
    />
    <p className="text-left">{`${w ? 'Error' : 'Aviso'}: ${coursePrefix}${diag.message}`}</p>
  </div>)
}

const ErrorTray = ({ diagnostics }: { diagnostics: Diagnostic[] }): JSX.Element => {
  const messageList: JSX.Element[] = diagnostics.map(diag => Message(diag))
  return (<div className="w-80 h-full overflow-hidden p-4 flex flex-col gap-4 border border-black border-dashed">
    {messageList.length > 0 ? messageList : <NoMessages/>}
  </div>)
}

export default ErrorTray
