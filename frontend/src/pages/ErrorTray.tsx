
import errorIcon from '../assets/error.svg'
import warningIcon from '../assets/warning.svg'
import okIcon from '../assets/ok.svg'

const NoMessages = (): JSX.Element => {
  return (<div className="flex flex-col items-center">
    <img className="w-10 h-10" src={okIcon} alt="No hay errores" />
    <p className="font-light">Todo OK!</p>
  </div>)
}

interface MessageParams {
  isWarning: boolean
  msg: string
}
const Message = (params: MessageParams): JSX.Element => {
  return (<div className={'flex flex-row items-center gap-4 ' + (params.isWarning ? 'font-normal' : 'font-medium')}>
    <img
      className="w-12 h-12"
      src={params.isWarning ? warningIcon : errorIcon}
      alt={params.isWarning ? 'Warning' : 'Error'}
    />
    <p className="text-left">{params.msg}</p>
  </div>)
}

const ErrorTray = ({ messages }: { messages: string[] }): JSX.Element => {
  const messageList: JSX.Element[] = messages.map(msg => Message({ isWarning: !msg.endsWith('!'), msg }))
  return (<div className="w-80 h-full overflow-hidden p-4 flex flex-col gap-4 border border-black border-dashed">
    {messageList.length > 0 ? messageList : <NoMessages/>}
  </div>)
}

export default ErrorTray
