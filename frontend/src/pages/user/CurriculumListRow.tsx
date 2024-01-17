import { type LowDetailPlanView } from '../../client'
import { Link } from '@tanstack/react-router'
import { ReactComponent as StarFull } from '../../assets/starFull.svg'
import { ReactComponent as StarOutline } from '../../assets/starOutline.svg'

interface RowProps {
  curriculum: LowDetailPlanView
  handleDelete?: Function
  handleFavourite?: Function
  openPlanNameModal: Function
  impersonateRut?: string
}

const CurriculumListRow = ({ curriculum, handleDelete, handleFavourite, openPlanNameModal, impersonateRut }: RowProps): JSX.Element => {
  function getDateString (date: string): string {
    const mydate = date.split('T')[0].split('-').reverse().join('-')
    return mydate
  }

  return (
        <tr className='bg-white border-b  hover:bg-gray-50 '>
          <td className='px-6 py-4'>
          {handleFavourite !== undefined &&
            <button onClick={() => handleFavourite(curriculum.id, curriculum.name, curriculum.is_favorite)}>{curriculum.is_favorite ? <StarFull /> : <StarOutline />}</button>
          }
          </td>
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
              <button className='text-green-600' onClick={() => openPlanNameModal(curriculum.id) }>Cambiar Nombre</button>
            </div></td>
        </tr>
  )
}

export default CurriculumListRow
