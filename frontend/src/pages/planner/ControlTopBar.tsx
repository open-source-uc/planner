
import { useAuth } from '../../contexts/auth.context'

interface ControlTopBarProps {
  reset: Function
  save: Function
  validating: boolean
}

function ControlTopBar ({ reset, save, validating }: ControlTopBarProps): JSX.Element {
  const authState = useAuth()

  return (
        <ul className="flex items-center  ml-3">
          <li className="inline mr-4 opacity-50 cursor-not-allowed">Exportar Malla</li>
          <li className={`inline mr-4 ${validating ? 'pointer-events-none' : ''}`}><button onClick={() => reset()}>Resetear Malla</button></li>
          {authState?.user != null && (<>
          <li className={`inline mr-4 ${validating ? 'pointer-events-none' : ''}`}><button onClick={() => save()}>Guardar Malla</button></li>
          </>)}
          <li className="inline mr-4 opacity-50 cursor-not-allowed">Ver Leyenda/ayuda</li>
          <li className="inline mr-4 opacity-50 cursor-not-allowed">Reportar Errores</li>
        </ul>)
}

export default ControlTopBar
