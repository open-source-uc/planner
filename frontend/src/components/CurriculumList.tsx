import CurriculumListRow from './CurriculumListRow'
import plusIcon from '../assets/plus.svg'
import { Link } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { DefaultService, LowDetailPlanView } from '../client'
import { Spinner } from './Spinner'

//   const curriculums = [
//     { id: 0, fav: true, name: 'Computación', creation: '10-01-2022', modified: '14-12-2022' },
//     { id: 1, fav: false, name: 'Diseno v2 esta si', creation: '10-03-2022', modified: '21-10-2022' },
//     { id: 2, fav: false, name: 'Diseno', creation: '10-10-2020', modified: '10-10-2020' },
//     { id: 3, fav: false, name: 'No seee', creation: '10-02-2020', modified: '14-12-2020' }
//   ]

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
    })
  }, [])

  async function handleDelete (id: string): Promise<void> {
    console.log('click', id)
    await DefaultService.deletePlan(id)
    readPlans().catch(err => {
      console.log(err)
    })
    console.log('plan deleted')
    alert('Malla eliminada exitosamente')
  }

  return (
      <div className="flex mb-4 h-full w-full"> {/* revisar si mejor con o sin items-center */}
          <div className="m-3 w-full">
                <div className="flex gap-4 items-center">
                    <h2 className="text-3xl font-medium leading-normal mb-2 text-gray-800 text-center">Mis mallas</h2>
                    <Link to="/planner">
                        <div className="hover-text">
                            <button><img className="w-8 h-8" src={plusIcon} alt="Crear nueva malla" /></button>
                            <span className="tooltip-text">Crear nueva malla</span>
                        </div>
                    </Link>
                </div>

                { loading && <div className="mt-5"><Spinner message="Cargando..." /></div> }

                { !loading && plans.length === 0 && <div className="mx-auto my-auto"><p className="text-gray-500 text-center">Todavía no tienes ninguna malla. Puedes partir <Link to="/planner" className='underline'>creando una nueva.</Link></p></div>}

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
