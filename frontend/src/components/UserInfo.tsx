const UserInfo = (): JSX.Element => {
  return (
    <>
        <div className="flex flex-col mb-4 h-full">
            <div className="h-1/2 m-3">
                <h3 className="text-4xl font-normal leading-normal mt-0 mb-2 text-gray-800">Información Personal</h3>
                <ul className="m-3 space-y-2">
                    <li>Nombre: Pepe Perez</li>
                    <li>Año Ingreso: 2020</li>
                    <li>Rut: 20426136-2</li>
                </ul>
            </div>
            <hr />
            <div className="h-1/2 m-3">
                <h3 className="text-4xl font-normal leading-normal mt-0 mb-2 text-gray-800">Información Académica (Según SIDING)</h3>
                <ul className="m-3 space-y-2">
                    <li>Título: No Inscrito</li>
                    <li>Major: Ingenieria Robotica</li>
                    <li>Minor: Amplitud Programacion</li>
                </ul>
            </div>
        </div>
    </>

  )
}

export default UserInfo
