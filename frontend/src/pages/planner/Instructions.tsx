
// const Description = ({ text }: { text: string }): JSX.Element => {
//   return (
//         <p className='ml-2 text-sm text-gray-500'>{text}</p>
//   )
// }

const Instructions = (): JSX.Element => {
  return (
    <div>
      <h3 className='text-xl font-medium leading-normal my-2 text-gray-800'>Selector major minor titulo</h3>
      <p>Para seleccionar un major, minor o título, hacer click en &apos;Por seleccionar&apos; o, si ya está selecionado, en el nombre del major, minor o título. </p>
      <p>Una vez seleccionado el major, el selector de minors solo mostratá los minors compatibles con el major seleccionado.</p>
      <p>Si se desea cambiar el major, teniendo el minor ya seleccionado, si existe una incompatibilidad, esta será informada.</p>
      <p>Al realizar cualquier cambio, el plan volverá a crear la malla recomendada para las opciones seleccionadas.</p>

      <h3 className='text-xl font-medium leading-normal my-2 text-gray-800'>Cursos</h3>
      <div className="my-1">
        <p>Selector cursos</p>
        <p>Para seleccionar o cambiar un curso correspondiente a optativos, hacer click en el simbolo del lapiz <></> en la tarjeta correspondiente.</p>
        <p>Se abrirá un selector en el cual se puede seleccionar el curso deseado de un grupo de cursos posibles.</p>
        <p>Dependiendo del bloque o equivalencia que se esté seleccionando, estos cursos se pueden filtrar por Nombre o Sigla, créditos, escuela y semestralidad.</p>
      </div>

      <div className="my-1">
        <p>Elim curso</p>
      </div>

      <div className="my-1">
        <p>Agregar curso</p>
      </div>

      <div className="my-1">
        <p>Drag Drop</p>
        <p>Para mover un curso, arrastrarlo y soltarlo en la posición deseada.</p>
        <p>Al arrastrar un curso, se muestan 2 columnas de semestres extra en la que se puede posicionar cursos.</p>
        <p>Los cursos de semestres ya cursados o en curso no se pueden mover.</p>
      </div>

      <h3 className='text-xl font-medium leading-normal my-2 text-gray-800'>Barra acciones</h3>
      <div className="my-1">
        <p>Guardar malla</p>
        <p> Para guardar la malla, hacer click en Guardar malla en la barra de acciones. Luego se abrirá un pop-up donde se debe dar un nombre a la malla y hacer click en aceptar</p>
        <p>Si la malla ya existía previamente, no volverá a preguntar el nombre.</p>
      </div>

      <div className="my-1">
        <p>Reestablecer malla</p>
      </div>

      <div className="my-1">
        <p>Exportar malla</p>
      </div>

      <div className="my-1">
        <p>Ver leyenda</p>
      </div>

      <div className="my-1">
        <p>Reportar errores</p>
      </div>

      <h3 className='text-xl font-medium leading-normal my-2 text-gray-800'>Bandeja errores y advertencias</h3>
      <div className="my-1">
        <p>Muestra los errores y advertencias relacionadas a los cursos o al plan en general.</p>
        <p>Lo errores se muestran en la parte superior de la bandeja, seguidos por las advertencias.</p>
        <p>Si no existen errores, la bandeja se puede minimizar.</p>
      </div>
    </div>

  )
}

export default Instructions
