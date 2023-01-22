import { LowDetailPlanView } from '../client'

const CurriculumListRow = ({ handleDelete, curriculum }: { handleDelete: Function, curriculum: LowDetailPlanView }): JSX.Element => {
  function getDateString (date: string): string {
    const mydate = date.split('T')[0].split('-').reverse().join('-')
    return mydate
  }

  return (
        <tr>
            {/* { curriculum.fav ? <td>★</td> : <td>☆</td>} */}
            <td><button type="button" onClick={(e) => { window.location.href = `/planner/${curriculum.id}` }} className='text-blue-600'>{curriculum.name}</button></td>
            <td>{getDateString(curriculum.created_at)}</td>
            <td>{getDateString(curriculum.updated_at)}</td>
            <td><div className='space-x-4 items-center'><button type="button" onClick={(e) => { window.location.href = `/planner/${curriculum.id}` }} className='text-blue-600'>Editar</button> <button className='text-red-600' onClick={() => handleDelete(curriculum.id)}>Eliminar</button></div></td>
        </tr>
  )
}

export default CurriculumListRow
