import { type LowDetailPlanView } from '../../client'
import { Link } from '@tanstack/react-router'

const CurriculumListRow = ({ curriculum, handleDelete, impersonateRut }: { curriculum: LowDetailPlanView, handleDelete?: Function, impersonateRut?: string }): JSX.Element => {
  function getDateString (date: string): string {
    const mydate = date.split('T')[0].split('-').reverse().join('-')
    return mydate
  }

  return (
        <tr className='bg-white border-b  hover:bg-gray-50 '>
            <th scope="row" className="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">
              {impersonateRut !== undefined
                ? <Link
                  className='text-blue-600'
                  to="/mod/planner/$userRut/$plannerId"
                  params={{
                    userRut: impersonateRut,
                    plannerId: curriculum.id
                  }}
                >{curriculum.name}
                </Link>
                : <Link
                  className='text-blue-600'
                  to="/planner/$plannerId"
                  params={{
                    plannerId: curriculum.id
                  }}
                >{curriculum.name}
                </Link>
              }
              </th>
            <td className='px-6 py-4'>{getDateString(curriculum.created_at)}</td>
            <td className='px-6 py-4'>{getDateString(curriculum.updated_at)}</td>
            <td className='px-6 py-4 text-right'><div className='space-x-4 items-center'>
              {impersonateRut !== undefined
                ? <Link
                  className='text-blue-600'
                  to="/mod/planner/$userRut/$plannerId"
                  params={{
                    userRut: impersonateRut,
                    plannerId: curriculum.id
                  }}
                >Editar
              </Link>
                : <Link
                  className='text-blue-600'
                  to="/planner/$plannerId"
                  params={{
                    plannerId: curriculum.id
                  }}
                >Editar
              </Link>
              }
              {handleDelete !== undefined &&
                <button className='text-red-600' onClick={() => handleDelete(curriculum.id)}>Eliminar</button>
              }
            </div></td>
        </tr>
  )
}

export default CurriculumListRow
