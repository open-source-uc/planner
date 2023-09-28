import SearchPlanByRutModal from './SearchPlanByRutModal'
import CurriculumListRow from '../user/CurriculumListRow'
import { useState } from 'react'
import { DefaultService, type StudentContext, type LowDetailPlanView } from '../../client'
import { Spinner } from '../../components/Spinner'
import { useQuery } from '@tanstack/react-query'
import { ReactComponent as PlusIcon } from '../../assets/plus.svg'
import { Link } from '@tanstack/react-router'
import { useAuth } from '../../contexts/auth.context'
import { isApiError } from '../planner/utils/Types'

async function fetchUserPlans (rut: string): Promise<LowDetailPlanView[]> {
  if (rut === '') return await Promise.resolve([])
  return await DefaultService.readAnyPlans(rut)
}

const UserViewer = (): JSX.Element => {
  const authState = useAuth()
  const [userRut, setUserRut] = useState<string>(authState?.student?.rut ?? '')
  const [searchingPlanModalIsOpen, setSearchingPlanModalIsOpen] = useState<boolean>(authState?.student?.rut === null)

  const { status, error, data } = useQuery({
    queryKey: ['userPlans', userRut],
    queryFn: async () => await fetchUserPlans(userRut)
  })

  const searchPlans = async (student: StudentContext, rut: string): Promise<void> => {
    let formattedRut = rut
    if (formattedRut.charAt(formattedRut.length - 2) !== '-') {
      formattedRut = formattedRut.slice(0, -1) + '-' + formattedRut.slice(-1)
    }
    if (authState?.setStudent !== null) {
      authState?.setStudent(prev => {
        if (prev !== null) return { ...student, rut: formattedRut }
        return prev
      })
    }
    setUserRut(formattedRut)
  }

  return (
    <div>
      <SearchPlanByRutModal
          isOpen = {searchingPlanModalIsOpen}
          onClose = {() => { setSearchingPlanModalIsOpen(false) }}
          searchPlans = {searchPlans}
      />
      <div className="flex my-2 h-full">
        <div className="mx-auto">
          <div className="flex mb-4 h-full w-full">
            <div className="m-3 w-full">
              <div className="flex gap-4 items-center">
                  <h2 className="text-3xl font-medium leading-normal mb-2 text-gray-800 text-center">Mallas del estudiante:</h2>
                  <button className="btn" onClick={() => {
                    setSearchingPlanModalIsOpen(true)
                  }}>{userRut !== '' ? 'Cambiar Estudiante' : 'Buscar Estudiante'}</button>
              </div>
              {status === 'success' && userRut !== '' &&
                <div className="flex gap-4 items-center">
                  <h2 className="text-2xl font-medium leading-normal mb-2 text-gray-800 text-center">{authState?.student?.info.full_name}</h2>
                  <Link to="mod/planner/new/$userRut"
                    params={{
                      userRut
                    }}>
                      <div className="hover-text">
                          <button><PlusIcon className="w-8 h-8" title="Ver malla nueva"/></button>
                          <span className="tooltip-text">Ver malla nueva</span>
                      </div>
                  </Link>
                </div>
              }
              {status === 'loading' && <div className="mt-5"><Spinner message="Cargando planificaciones..." /></div>}

              {status === 'error' && <div className="mx-auto my-auto"><p className="text-gray-500 text-center">{isApiError(error) && error.message}</p></div>}

              {status === 'success' && userRut === '' && <div className="mx-auto my-auto"><p className="text-gray-500 text-center">Ingresa el rut del estudiante para buscar sus mallas.</p></div>}

              {(status === 'success' && userRut !== '') && (data.length === 0
                ? <div className="mx-auto my-auto"><p className="text-gray-500 text-center">El usuario no tiene ninguna malla.</p></div>
                : <div className='relative overflow-x-auto shadow-md sm:rounded-lg max-w-2xl mt-2'>
                  <table className="w-full text-sm text-left text-gray-500">
                    <thead className="text-xs text-gray-700 uppercase bg-gray-50 ">
                      <tr className="border-b-4 border-gray-600">
                          {/* <th></th> para favourite */}
                          <th scope="col" className="px-6 py-3">Nombre</th>
                          <th scope="col" className="px-6 py-3">Fecha Creación</th>
                          <th scope="col" className="px-6 py-3">Fecha Modificación</th>
                          <th scope="col" className="px-6 py-3"><span className="sr-only">Acciones</span></th>
                      </tr>
                    </thead>
                    <tbody className='bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600'>
                      {data?.map((plan: LowDetailPlanView) => {
                        return (
                          <CurriculumListRow key={plan.id} curriculum={plan} impersonateRut={userRut}/>
                        )
                      })}
                    </tbody>
                  </table>
                </div>)}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default UserViewer
