import { Link } from '@tanstack/react-router'

const CurriculumListRow = ({ handleDelete, curriculum }: { handleDelete: Function, curriculum: { id: number, fav: boolean, name: string, creation: string, modified: string } }): JSX.Element => {
  return (
        <tr>
            { curriculum.fav ? <td>★</td> : <td>☆</td>}
            <td><Link to="/planner">{curriculum.name}</Link></td>
            <td>{curriculum.creation}</td>
            <td>{curriculum.modified}</td>
            <td><div className='space-x-4 items-center'><button className='text-blue-600'>Editar</button> <button className='text-red-600' onClick={() => handleDelete()}>Eliminar</button></div></td>
        </tr>
  )
}

export default CurriculumListRow
