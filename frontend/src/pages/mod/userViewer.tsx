import SearchPlanByRutModal from './SearchPlanByRutModal'
import CurriculumListRow from './CurriculumListViewerRow'
import { useState } from 'react'
import { DefaultService, type LowDetailPlanView } from '../../client'
import { Spinner } from '../../components/Spinner'
import { useQuery } from '@tanstack/react-query'

async function fetchUserPlans (rut: string): Promise<LowDetailPlanView[]> {
  if (rut === '') return await Promise.resolve([])
  return await DefaultService.readAnyPlans(rut)
}

const UserViewer = (): JSX.Element => {
  const [userRut, setUserRut] = useState<string>('')

  const { status, error, data } = useQuery({
    queryKey: ['userPlans', userRut],
    queryFn: async () => await fetchUserPlans(userRut)
  })

  const [searchingPlanModalIsOpen, setSearchingPlanModalIsOpen] = useState<boolean>(true)
  return (
    <div>
      <SearchPlanByRutModal
          isOpen = {searchingPlanModalIsOpen}
          onClose = {() => { setSearchingPlanModalIsOpen(false) }}
          searchPlans = {(rut: string) => { setUserRut(rut) } }
      />

      <div className="flex my-2 h-full">
        <div className="mx-auto">
          <div className="flex mb-4 h-full w-full">
            <div className="m-3 w-full">
              <div className="flex gap-4 items-center">
                  <h2 className="text-3xl font-medium leading-normal mb-2 text-gray-800 text-center">Mallas del estudiante</h2>
                  <button className="btn" onClick={() => {
                    setSearchingPlanModalIsOpen(true)
                  }}>Buscar Estudiante</button>
              </div>
              {status === 'loading' && <div className="mt-5"><Spinner message="Cargando planificaciones..." /></div>}

              {status === 'error' && <div className="mx-auto my-auto"><p className="text-gray-500 text-center">{error.message}</p></div>}

              {status === 'success' && userRut === '' && <div className="mx-auto my-auto"><p className="text-gray-500 text-center">Ingresa el rut del estudiante para buscar sus mallas.</p></div>}

              {(status === 'success' && userRut !== '') && (data.length === 0
                ? <div className="mx-auto my-auto"><p className="text-gray-500 text-center">Este usuario no tiene ninguna malla.</p></div>
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
                          <CurriculumListRow key={plan.id} userRut={userRut} curriculum={plan}/>
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
