import errorIcon from '../../assets/error.svg'
import warningIcon from '../../assets/warning.svg'
import okIcon from '../../assets/ok.svg'
import { FlatDiagnostic } from '../../client'

/**
 * This is what is displayed when there are no errors or warnings.
 */
const NoMessages = (): JSX.Element => {
  return (<div className="flex flex-col items-center">
    <img className="w-10 h-10" src={okIcon} alt="No hay errores" />
    <p className="font-light">Todo OK!</p>
  </div>)
}

/**
 * A single error/warning message.
 */
const Message = (diag: FlatDiagnostic, key: number): JSX.Element => {
  const w = diag.is_warning
  const coursePrefix = diag.course_code == null ? '' : `${diag.course_code}: `
  return (<div key={key} className={'flex flex-row items-center gap-4 ' + (w ? 'font-normal' : 'font-medium')}>
    <img
      className="w-12 h-12"
      src={w ? warningIcon : errorIcon}
      alt={w ? 'Warning' : 'Error'}
    />
    <p className="text-left">{`${w ? 'Aviso' : 'Error'}: ${coursePrefix}${diag.message}`}</p>
  </div>)
}

/**
 * The error tray shows errors and warnings about the current plan that come from the validation backend.
 */
const ErrorTray = ({ diagnostics, validating }: { diagnostics: FlatDiagnostic[], validating: boolean }): JSX.Element => {
  const messageList: JSX.Element[] = diagnostics.map((diag, index) => Message(diag, index))
  return (<div className="w-80 h-full overflow-x-hidden overflow-y-auto p-4 flex flex-col gap-4 border border-black border-dashed">
    {validating ? <p className="font-medium">Validando...</p> : <>{messageList.length > 0 ? messageList : <NoMessages/>}</>}
  </div>)
}

export default ErrorTray
