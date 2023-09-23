interface ControlTopBarProps {
  authState: any
  reset: Function
  openLegendModal: Function
  openSavePlanModal: Function
}

function ControlTopBar ({ authState, reset, openLegendModal, openSavePlanModal }: ControlTopBarProps): JSX.Element {
  return (
        <ul className="flex items-center  ml-3 mb-2 gap-6">
          {authState?.user != null && (<>
          <li className='inline'><button onClick={() => openSavePlanModal() }>Guardar malla</button></li>
          </>)}
          <li className='inline'><button onClick={() => reset()}>Restablecer malla</button></li>
          {/* <li className="inline opacity-50 cursor-not-allowed">Exportar malla</li> */}
          <li className="inline"><button onClick={() => openLegendModal()}>Ver leyenda</button></li>
          <li className="inline"><a href="https://github.com/open-source-uc/planner/issues?q=is%3Aopen+is%3Aissue+label%3Abug" rel="noreferrer" target="_blank">Reportar errores</a></li>
        </ul>)
}

export default ControlTopBar
