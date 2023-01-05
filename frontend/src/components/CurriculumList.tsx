const CurriculumList = (): JSX.Element => {
  return (
      <div className="flex mb-4 h-full w-full">
          <div className=" bg-green-300 m-3 w-full">
                <h2>Listado de Mallas</h2>
                <table className="table-auto text-center w-full h-full p-3 "> {/* revisar si mejor con o sin h-full */}
                    <tr className="border-b-4 border-gray-600">
                        <th></th>
                        <th>Nombre</th>
                        <th>Fecha Creación</th>
                        <th>Fecha Modificación</th>
                        <th>Acciones</th>
                    </tr>
                    <tr>
                        <td>★</td>
                        <td>Computación</td>
                        <td>10-01-2022</td>
                        <td>14-12-2022</td>
                        <td>edit delete duplicate</td>
                    </tr>
                    <tr>
                        <td>☆</td>
                        <td>Diseno v2 esta si</td>
                        <td>10-03-2022</td>
                        <td>21-10-2022</td>
                        <td>edit delete duplicate</td>
                    </tr>
                    <tr>
                        <td>☆</td>
                        <td>Diseno</td>
                        <td>10-10-2020</td>
                        <td>10-10-2020</td>
                        <td>edit delete duplicate</td>
                    </tr>
                    <tr>
                        <td>☆</td>
                        <td>No seee</td>
                        <td>10-02-2020</td>
                        <td>14-12-2020</td>
                        <td>edit delete duplicate</td>
                    </tr>
                </table>
          </div>
      </div>

  )
}

export default CurriculumList
