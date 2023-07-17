import { useAuth } from '../../contexts/auth.context'

interface ControlTopBarProps {
  reset: Function
  openSavePlanModal: Function
  openLegendModal: Function
}

function ControlTopBar ({ reset, openSavePlanModal, openLegendModal }: ControlTopBarProps): JSX.Element {
  const authState = useAuth()

  return (
        <ul className="flex items-center  ml-3 mb-2 gap-6">
          {authState?.user != null && (<>
          <li className='inline'><button onClick={() => openSavePlanModal()}>Guardar malla</button></li>
          </>)}
          <li className='inline'><button onClick={() => reset()}>Restablecer malla</button></li>
          <li className="inline opacity-50 cursor-not-allowed">Exportar malla</li>
          <li className="inline"><button onClick={() => openLegendModal()}>Ver leyenda</button></li>
          <li className="inline"><a href="https://github.com/open-source-uc/planner/issues?q=is%3Aopen+is%3Aissue+label%3Abug" rel="noreferrer" target="_blank">Reportar errores</a></li>
        </ul>)
}

export default ControlTopBar
