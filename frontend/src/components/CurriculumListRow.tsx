const CurriculumListRow = ({ curriculum }: { curriculum: { id: number, fav: boolean, name: string, creation: string, modified: string } }): JSX.Element => {
  return (
        <tr>
            { curriculum.fav ? <td>★</td> : <td>☆</td>}
            <td>{curriculum.name}</td>
            <td>{curriculum.creation}</td>
            <td>{curriculum.modified}</td>
            <td>edit delete duplicate</td>
        </tr>
  )
}

export default CurriculumListRow
