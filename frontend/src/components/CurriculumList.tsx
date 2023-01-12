import CurriculumListRow from './CurriculumListRow'
import plusIcon from '../assets/plus.svg'
import { Link } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { DefaultService } from '../client'

//   const curriculums = [
//     { id: 0, fav: true, name: 'Computación', creation: '10-01-2022', modified: '14-12-2022' },
//     { id: 1, fav: false, name: 'Diseno v2 esta si', creation: '10-03-2022', modified: '21-10-2022' },
//     { id: 2, fav: false, name: 'Diseno', creation: '10-10-2020', modified: '10-10-2020' },
//     { id: 3, fav: false, name: 'No seee', creation: '10-02-2020', modified: '14-12-2020' }
//   ]

const CurriculumList = (): JSX.Element => {
  const [plans, setPlans] = useState([])

  useEffect(() => {
    const readPlans = async (): Promise<void> => {
      console.log('getting Plans ...')
      const response = await DefaultService.readPlans()
      setPlans(response)
      console.log('data loaded')
      console.log(plans)
    }
    readPlans().catch(err => {
      console.log(err)
    })
  }, [])

  function handleDelete (): void {
    console.log('click')
  }

  return (
      <div className="flex  mb-4 h-full w-full"> {/* revisar si mejor con o sin items-center */}
          <div className=" bg-green-300 m-3 w-full">
                <div className="flex space-x-4 items-center">
                    <h2 className="text-5xl font-normal leading-normal mt-0 mb-2 text-gray-800">Listado de Mallas</h2>
                    <Link to="/planner">
                        <div className="hover-text">
                            <button><img className="w-10 h-10" src={plusIcon} alt="Nueva Malla" /></button>
                            <span className="tooltip-text">Crear Nueva Malla</span>
                        </div>
                    </Link>
                </div>

                <table className="table-auto text-center w-full p-3">
                    <tr className="border-b-4 border-gray-600">
                        <th></th>
                        <th>Nombre</th>
                        <th>Fecha Creación</th>
                        <th>Fecha Modificación</th>
                        <th>Acciones</th>
                    </tr>

                    {plans?.map((plan) => {
                      return (
                            <CurriculumListRow key={1} handleDelete={handleDelete} curriculum={plan}/>
                      )
                    })}

                    <CurriculumListRow handleDelete={handleDelete} curriculum={{ id: 0, fav: true, name: 'Computación', creation: '10-01-2022', modified: '14-12-2022' }}/>
                    <CurriculumListRow handleDelete={handleDelete} curriculum={{ id: 1, fav: false, name: 'Diseno v2 esta si', creation: '10-03-2022', modified: '21-10-2022' }}/>
                    <CurriculumListRow handleDelete={handleDelete} curriculum={{ id: 2, fav: false, name: 'Diseno', creation: '10-10-2020', modified: '10-10-2020' }}/>
                    <CurriculumListRow handleDelete={handleDelete} curriculum={{ id: 3, fav: false, name: 'No seee', creation: '10-02-2020', modified: '14-12-2020' }}/>
                </table>
          </div>
      </div>

  )
}

export default CurriculumList
