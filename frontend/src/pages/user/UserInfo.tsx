import { useAuth } from '../../contexts/auth.context'

const UserInfo = (): JSX.Element => {
  const authState = useAuth()

  return (
    <>
      <div className="flex flex-col mb-4 h-full sentry-mask">
          <div className="h-1/2 m-3">
              <h3 className="text-4xl font-normal leading-normal mt-0 mb-2 text-gray-800">Información Personal</h3>
              <ul className="m-3 space-y-2">
                  <li>Nombre: {authState?.student?.info?.full_name}</li>
                  {/* TODO: Fix this when we have time */}
                  {/* <li>Ingreso: {String(authState?.student?.admission.slice(0, -1)) + '-' + String(authState?.student?.info?.admission.slice(-1))}</li> */}
                  <li>Rut: 20426136-2 </li>
              </ul>
          </div>
          <hr />
          <div className="h-1/2 m-3">
              <h3 className="text-4xl font-normal leading-normal mt-0 mb-2 text-gray-800">Información Académica (Según SIDING)</h3>
              <ul className="m-3 space-y-2">
                  <li>Título: {authState?.student?.info?.reported_title ?? 'No Inscrito'} </li>
                  <li>Major: {authState?.student?.info?.reported_major ?? 'No declarado'} </li>
                  <li>Minor: {authState?.student?.info?.reported_minor ?? 'No declarado'} </li>
              </ul>
          </div>
      </div>
    </>

  )
}

export default UserInfo
