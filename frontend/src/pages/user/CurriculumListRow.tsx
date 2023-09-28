import { type LowDetailPlanView } from '../../client'
import { Link } from '@tanstack/react-router'

const CurriculumListRow = ({ curriculum, handleDelete }: { curriculum: LowDetailPlanView, handleDelete?: Function }): JSX.Element => {
  function getDateString (date: string): string {
    const mydate = date.split('T')[0].split('-').reverse().join('-')
    return mydate
  }

  return (
        <tr className='bg-white border-b  hover:bg-gray-50 '>
            <th scope="row" className="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">
              <Link
                className='text-blue-600'
                to="/planner/$plannerId"
                params={{
                  plannerId: curriculum.id
                }}
              >{curriculum.name}
              </Link>
              </th>
            <td className='px-6 py-4'>{getDateString(curriculum.created_at)}</td>
            <td className='px-6 py-4'>{getDateString(curriculum.updated_at)}</td>
            <td className='px-6 py-4 text-right'><div className='space-x-4 items-center'>
              <Link
                  className='text-blue-600'
                  to="/planner/$plannerId"
                  params={{
                    plannerId: curriculum.id
                  }}
                >Editar
              </Link>
              {handleDelete !== undefined &&
                <button className='text-red-600' onClick={() => handleDelete(curriculum.id)}>Eliminar</button>
              }
            </div></td>
        </tr>
  )
}

export default CurriculumListRow
