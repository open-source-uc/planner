import { useAuth } from '../../contexts/auth.context'
import { useEffect } from 'react'

const UserInfo = (): JSX.Element => {
  const authState = useAuth()

  useEffect(() => {
    console.log(authState)
  }, [])

  return (
    <>
      <div className="flex flex-col mb-4 h-full">
          <div className="h-1/2 m-3">
              <h3 className="text-4xl font-normal leading-normal mt-0 mb-2 text-gray-800">Información Personal</h3>
              <ul className="m-3 space-y-2">
                  <li>Nombre: {authState?.info?.full_name}</li>
                  <li>Ingreso: {String(authState?.info?.admission.slice(0, -1)) + '-' + String(authState?.info?.admission.slice(-1))}</li>
                  <li>Rut: 20426136-2 </li>
              </ul>
          </div>
          <hr />
          <div className="h-1/2 m-3">
              <h3 className="text-4xl font-normal leading-normal mt-0 mb-2 text-gray-800">Información Académica (Según SIDING)</h3>
              <ul className="m-3 space-y-2">
                  <li>Título: {((authState?.info?.reported_title) != null) ? authState?.info?.reported_title : 'No Inscrito'} </li>
                  <li>Major: {((authState?.info?.reported_major) != null) ? authState?.info?.reported_major : 'No declarado'} </li>
                  <li>Minor: {((authState?.info?.reported_minor) != null) ? authState?.info?.reported_minor : 'No declarado'} </li>
              </ul>
          </div>
      </div>
    </>

  )
}

export default UserInfo
