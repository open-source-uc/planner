
import { useAuth } from '../../contexts/auth.context'

interface ControlTopBarProps {
  reset: Function
  save: Function
  validating: boolean
}

function ControlTopBar ({ reset, save, validating }: ControlTopBarProps): JSX.Element {
  const authState = useAuth()

  return (
        <ul className="flex items-center  ml-3 mb-2 gap-6">
          {authState?.user != null && (<>
          <li className={`inline ${validating ? 'pointer-events-none' : ''}`}><button onClick={() => save()}>Guardar malla</button></li>
          </>)}
          <li className={`inline ${validating ? 'pointer-events-none' : ''}`}><button onClick={() => reset()}>Restablecer malla</button></li>
          <li className="inline opacity-50 cursor-not-allowed">Exportar malla</li>
          <li className="inline opacity-50 cursor-not-allowed">Ver leyenda</li>
          <li className="inline opacity-50 cursor-not-allowed">Reportar errores</li>
        </ul>)
}

export default ControlTopBar
