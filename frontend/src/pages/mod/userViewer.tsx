import SearchPlanByRutModal from './SearchPlanByRutDialog'
import CurriculumListRow from '../user/CurriculumListRow'
import { useState } from 'react'
import { DefaultService, type LowDetailPlanView } from '../../client'
import { Spinner } from '../../components/Spinner'
import { useSearch, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { ReactComponent as PlusIcon } from '../../assets/plus.svg'
import { type Student } from '../../contexts/auth.context'
import { isApiError } from '../planner/utils/Types'
import { useAuth } from '../../contexts/auth.context'

function formattedRut (rut: string): string {
  let formattedRut = rut
  if (rut.length > 1 && formattedRut.charAt(formattedRut.length - 2) !== '-') {
    formattedRut = formattedRut.slice(0, -1) + '-' + formattedRut.slice(-1)
  }
  return formattedRut
}
async function fetchUserPlans (rut: string | undefined): Promise<LowDetailPlanView[]> {
  if (rut === '' || rut === undefined) return await Promise.resolve([])
  return await DefaultService.readAnyPlans(rut)
}

async function fetchStudentInfo (rut: string): Promise<Student | null> {
  if (rut === '') { return null }
  const response = await DefaultService.getStudentInfoForAnyUser(rut)
  return { ...response, rut }
}

const UserViewer = (): JSX.Element => {
  const authState = useAuth()
  const { studentRut } = useSearch({ from: '/mod/users' })
  const [userRut, setUserRut] = useState<string>(formattedRut(studentRut))
  const [searchingPlanModalIsOpen, setSearchingPlanModalIsOpen] = useState<boolean>(studentRut === '')

  const { status: studentDataStatus, error: studentDataError, data: studentInfo } = useQuery({
    queryKey: ['studentInfo', userRut],
    retry: false,
    onSuccess: (data: Student | null) => {
      if (data !== undefined && data !== null) {
        setSearchingPlanModalIsOpen(false)
        if (authState?.setStudent !== null) {
          authState?.setStudent(data)
        }
      }
    },
    onError: () => {
      setSearchingPlanModalIsOpen(true)
    },
    queryFn: async () => await fetchStudentInfo(userRut)
  })

  const { status: studentPlansStatus, error: studentPlansError, data: studentPlans } = useQuery({
    queryKey: ['studentPlans', studentInfo],
    retry: false,
    queryFn: async () => await fetchUserPlans(studentInfo?.rut)
  })
  const isStudentSearched = studentInfo?.rut === userRut
  return (
    <div>
      <SearchPlanByRutModal
          isOpen = {searchingPlanModalIsOpen}
          onClose = {() => { setSearchingPlanModalIsOpen(false) }}
          status = {studentDataStatus}
          error = {studentDataError}
          studentInitialSearch = {studentRut}
          searchUser = {(rut: string) => { setUserRut(formattedRut(rut)) }}
      />
      <div className="flex my-2 h-full">
        <div className="mx-auto">
          <div className="flex mb-4 h-full w-full">
            <div className="m-3 w-full">
              <div className="flex gap-4 items-center">
                  <h2 className="text-3xl font-medium leading-normal mb-2 text-gray-800 text-center">Mallas del estudiante:</h2>
                  <button className="btn" onClick={() => {
                    setSearchingPlanModalIsOpen(true)
                  }}>{isStudentSearched ? 'Cambiar Estudiante' : 'Buscar Estudiante'}</button>
              </div>
              {studentPlansStatus === 'success' && isStudentSearched &&
                <div className="flex gap-4 items-center">
                  <h2 className="text-2xl font-medium leading-normal mb-2 text-gray-800 text-center">{studentInfo?.full_name}</h2>
                  <Link to="/mod/planner/new/$userRut"
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
              {studentPlansStatus === 'loading' && <div className="mt-5"><Spinner message="Cargando planificaciones..." /></div>}

              {studentPlansStatus === 'error' && <div className="mx-auto my-auto"><p className="text-gray-500 text-center">{isApiError(studentPlansError) && studentPlansError.message}</p></div>}

              {studentPlansStatus === 'success' && !isStudentSearched && <div className="mx-auto my-auto"><p className="text-gray-500 text-center">Ingresa el rut del estudiante para buscar sus mallas.</p></div>}

              {(studentPlansStatus === 'success' && studentInfo?.rut === userRut) && (studentPlans.length === 0
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
                      {studentPlans?.map((plan: LowDetailPlanView) => {
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
