import { Link } from '@tanstack/react-router'

const CurriculumListRow = ({ handleDelete, curriculum }: { handleDelete: Function, curriculum: { id: string, name: string, created_at: string, updated_at: string } }): JSX.Element => {
  function getDateString (date: string): string {
    const mydate = date.split('T')[0].split('-').reverse().join('-')
    return mydate
  }

  return (
        <tr>
            {/* { curriculum.fav ? <td>★</td> : <td>☆</td>} */}
            <td><Link to="/planner" className='text-blue-600'>{curriculum.name}</Link></td>
            <td>{getDateString(curriculum.created_at)}</td>
            <td>{getDateString(curriculum.updated_at)}</td>
            <td><div className='space-x-4 items-center'><button className='text-blue-600'>Editar</button> <button className='text-red-600' onClick={() => handleDelete(curriculum.id)}>Eliminar</button></div></td>
        </tr>
  )
}

export default CurriculumListRow
