import CurriculumListRow from './CurriculumListRow'
import { ReactComponent as PlusIcon } from '../../assets/plus.svg'
import { Link } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { DefaultService, type LowDetailPlanView, type ApiError } from '../../client'
import { Spinner } from '../../components/Spinner'
import { toast } from 'react-toastify'

const isApiError = (err: any): err is ApiError => {
  return err.status !== undefined
}

const CurriculumList = (): JSX.Element => {
  const [plans, setPlans] = useState <LowDetailPlanView[]>([])
  const [loading, setLoading] = useState <boolean>(true)

  const readPlans = async (): Promise<void> => {
    const response = await DefaultService.readPlans()
    setPlans(response)
    setLoading(false)
  }

  useEffect(() => {
    readPlans().catch(err => {
      console.log(err)
      if (err.status === 401) {
        console.log('token invalid or expired, loading re-login page')
        toast.error('Tu session a expirado. Redireccionando a pagina de inicio de sesion...', {
          toastId: 'ERROR401'
        })
      }
    })
  }, [])
  async function handleDelete (id: string): Promise<void> {
    try {
      console.log('click', id)
      await DefaultService.deletePlan(id)
      await readPlans()
      console.log('plan deleted')
      toast.success('Malla eliminada exitosamente')
    } catch (err) {
      console.log(err)
      if (isApiError(err) && err.status === 401) {
        console.log('token invalid or expired, loading re-login page')
        toast.error('Token invalido. Redireccionando a pagina de inicio...')
      }
    }
  }

  return (
      <div className="flex mb-4 h-full w-full">
          <div className="m-3 w-full">
                <div className="flex gap-4 items-center">
                    <h2 className="text-3xl font-medium leading-normal mb-2 text-gray-800 text-center">Mis mallas</h2>
                    <Link to="/planner/new">
                        <div className="hover-text">
                            <button><PlusIcon className="w-8 h-8" title="Crear nueva malla"/></button>
                            <span className="tooltip-text">Crear nueva malla</span>
                        </div>
                    </Link>
                </div>

                { loading && <div className="mt-5"><Spinner message="Cargando planificaciones..." /></div> }

                { !loading && plans.length === 0 && <div className="mx-auto my-auto"><p className="text-gray-500 text-center">Todavía no tienes ninguna malla. Puedes partir <Link to="/planner/new" className='underline'>creando una nueva.</Link></p></div>}

                { !loading && plans.length > 0 && <div className='relative overflow-x-auto shadow-md sm:rounded-lg max-w-2xl mt-2'>
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
                    {plans?.map((plan: LowDetailPlanView) => {
                      return (
                              <CurriculumListRow key={plan.id} handleDelete={handleDelete} curriculum={plan}/>
                      )
                    })}
                  </tbody>

                </table>
                </div>}
          </div>
      </div>

  )
}

export default CurriculumList
