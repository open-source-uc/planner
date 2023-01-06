
import { useAuth } from '../../contexts/auth.context'

function ControlTopBar ({ reset }: { reset: Function }): JSX.Element {
  const authState = useAuth()

  return (
        <ul className="flex items-center">
          <li className="inline mr-4 opacity-50 cursor-not-allowed">Exportar Malla</li>
          <li className="inline mr-4"><button onClick={() => reset()}>Resetear Malla</button></li>
          {authState?.user != null && (<>
          <li className="inline mr-4 opacity-50 cursor-not-allowed">Guardar Malla</li>
          <li className="inline mr-4 opacity-50 cursor-not-allowed">Borrar Malla</li>
          </>)}
          <li className="inline mr-4 opacity-50 cursor-not-allowed">Ver Leyenda/ayuda</li>
          <li className="inline mr-4 opacity-50 cursor-not-allowed">Reportar Errores</li>
        </ul>)
}

export default ControlTopBar
