
import selectorEmpty from '../../../assets/instructions/selector_empty.jpg'
import selectorFull from '../../../assets/instructions/selector_full.jpg'
import selectorDropdown from '../../../assets/instructions/selector_dropdown.jpg'
import selectorIncompatibility from '../../../assets/instructions/selector_incompatibility.jpg'
import selectorDelete from '../../../assets/instructions/selector_delete.jpg'
import editIcon from '../../../assets/editBlack.svg'
import courseSelector from '../../../assets/instructions/courseSelector.jpg'
import courseSelectorNoFilter from '../../../assets/instructions/courseSelector_nofilter.jpg'
import contextMore from '../../../assets/instructions/contextMenu_mas.jpg'
import contextAsign from '../../../assets/instructions/contextMenu_asignar.jpg'
import quickFix from '../../../assets/instructions/quickFix.jpg'

const Text = ({ text }: { text: string }): JSX.Element => {
  return (
        <p className='ml-3 text-sm text-gray-600'>{text}</p>
  )
}

const Subtitle = ({ text }: { text: string }): JSX.Element => {
  return (
        <p className='ml-2 text-base text-gray-800'>{text}</p>
  )
}

const SectionTitle = ({ text }: { text: string }): JSX.Element => {
  return (
        <h3 className='text-xl font-medium leading-normal mb-3 text-blue-800'>{text}</h3>
  )
}

const Instructions = (): JSX.Element => {
  return (
    <div className='text-justify'>
      <div className='mb-4'>
        <SectionTitle text='Selector major minor titulo' />
        <Text text={'Para seleccionar un major, minor o título, hacer click en \'Por seleccionar\'.'}/>
        <img className="w-2/3 m-1 mb-3 mx-auto h-auto" alt="selector empty" src={selectorEmpty}></img>

        <Text text='Si ya está selecionado el major, minor o título y se desea modificar, hacer click en el nombre correspondiente.'/>
        <img className="w-auto m-1 mb-3 mx-auto h-3/5" alt="selector full" src={selectorFull}></img>

        <Text text='Se abrirá una lista con las opciones disponibles. Simplemente hacer click en la deseada.' />
        <img className="w-1/3 m-1 mb-3 mx-auto h-auto" alt="selector list of majors" src={selectorDropdown}></img>

        <Text text='Una vez seleccionado el major, el selector de minors solo mostrará los minors compatibles con el major seleccionado.'/>

        <Text text='Si se desea cambiar el major teniendo el minor ya seleccionado, si existe una incompatibilidad, esta será informada.'/>
        <img className="w-1/3 m-1 mb-3 mx-auto h-auto" alt="Alerta incompatibilidad" src={selectorIncompatibility}></img>

        <Text text={'Si se desea eliminar una selección, esto se puede realizar haciendo click en \'Eliminar selección\' en la parte superior de la lista.'}/>
        <img className="w-1/3 m-1 mb-3 mx-auto h-auto" alt="Eliminar selección" src={selectorDelete}></img>

        <Text text='Al realizar cualquier cambio, el plan volverá a crear la malla recomendada para las opciones seleccionadas.'/>
      </div>

      <div className='mb-4'>
        <SectionTitle text='Cursos' />
        <div className="mb-2">
          <Subtitle text='Selector cursos' />
          <p className='ml-3 text-sm text-gray-600'> Para seleccionar o cambiar un curso correspondiente a optativos, hacer click en el símbolo del lápiz <img className='opacity-60 relative inline-block w-3' src={editIcon} alt="Seleccionar Curso" /> que se encuentra
           en la esquina superior izquierda de la tarjeta, en la tarjeta correspondiente.</p>
          <Text text='Se abrirá un selector en el cual se puede seleccionar el curso deseado de un grupo de cursos posibles.'/>
          <Text text='Dependiendo del bloque o equivalencia que se esté seleccionando, estos cursos se pueden filtrar por Nombre o Sigla, créditos, escuela y semestralidad.'/>
          <span className='flex flex-row'>
            <img className="w-1/3 m-1 mb-3 mx-auto h-auto" alt="selector de curso con filtros" src={courseSelector}></img>
            <img className="w-1/3 m-1 mb-3 mx-auto h-auto" alt="selector de curso sin filtros" src={courseSelectorNoFilter}></img>
          </span>
        </div>

        <div className="mb-2">
          <Subtitle text='Eliminar curso' />
          <Text text='En cursos no pertenecientes a los bloques de la malla, existe la posibilidad de eliminarlos. Para ello, simplemente hacer click en la X que aparece
            en la esquina superior derecha de la tarjeta al hacer hover con el mouse.'/>
            {/* <Text text='No se pueden eliminar cursos de semestres cursados o en curso.'/> */}
        </div>

        <div className="my-2">
          <Subtitle text='Agregar curso' />
          <Text text='Para agregar un nuevo curso, que no es parte de alguna equivalencia u optativo que se deba elegir (para lo que se ocupa el selector antes mencionado), hacer click en el botón +
            que se encuentra al final de cada columna correspondiente a un semeste.'/>
          <Text text='Al hacer click en este botón, se abrirá un modal similar al del selector de cursos, donde podrá aplicar filtros para encontrar el ramo deseado.'/>
          <Text text='No se pueden agregar cursos a semestres cursados o en curso.'/>
        </div>

        <div className="my-2">
          <Subtitle text='Mover cursos (Drag & Drop)' />
          <Text text='Para mover un curso, arrastrarlo y soltarlo en la posición deseada.'/>
          <Text text='Al arrastrar un curso, se muestan 2 columnas de semestres extra en la que se puede posicionar cursos.'/>
          <Text text='Los cursos de semestres ya cursados o en curso no se pueden mover.'/>
        </div>

        <div className="my-2">
          <Subtitle text='Otras acciones (Botón Derecho)' />
          <Text text='Al hacer click en curso con el botón derecho del mouse se abrirá un menú con varias opciones.'/>
          <Text text='Al poner el mouse sobre "Más información", se mostrarán 3 opciones que dirigen al sitio oficial del curso.'/>
          <img className="w-1/3 m-1 mb-3 mx-auto h-auto" alt="context menu más información" src={contextMore}></img>

          <Text text='Al poner el mouse sobre "Asignar como", se mostrarán aquellos bloques a los que el curso puede ser asignado, mostrando con ✔ aquel bloque actualmente asignado,
          o ❗ si existe algun problema con la asignación.'/>
          <img className="w-1/3 m-1 mb-3 mx-auto h-auto" alt="context menu asignar como" src={contextAsign}></img>

          <Text text='Además, en cursos en semetres en curso o futuros, también se puede eliminar el curso seleccionado.'/>

        </div>
      </div>

      <div className='mb-4'>
        <SectionTitle text='Barra acciones' />
        <div className="my-2">
          <Subtitle text='Guardar malla' />
          <Text text='Para guardar la malla, hacer click en Guardar malla en la barra de acciones. Luego se abrirá un pop-up donde se debe dar un nombre a la malla y hacer click en aceptar.'/>
          <Text text='Si la malla ya existía previamente, no volverá a preguntar el nombre.'/>
        </div>

        <div className="mb-2">
          <Subtitle text='Reestablecer malla' />
          <Text text='Esta opción revierte los cambios realizados desde la ultima vez en que se guardó la malla.'/>
        </div>

        <div className="mb-2">
          <Subtitle text='Exportar malla' />
          <Text text='Esta opción genera un archivo pdf de la malla que se encuentra en pantalla.'/>
        </div>

        <div className="mb-2">
          <Subtitle text='Ver leyenda' />
          <Text text='Este botón abre la leyenda e instrucciones del planner, es decir, el modal que está leyendo en este momento.'/>
        </div>

        <div className="mb-2">
          <Subtitle text='Reportar errores' />
          <Text text={'Para reportar errores, hacer click en el boton Reportar errores, este lo redirigirá al repositorio en github donte podrá escribir una \'issue\' describiendo el problema.'}/>
        </div>
      </div>

      <div className='mb-4'>
        <SectionTitle text='Bandeja errores y advertencias' />
        <Text text='Muestra los errores y advertencias relacionadas a los cursos o al plan en general.'/>
        <Text text='Algunos muestran botones que permiten realizar arreglos de forma automática.'/>
        <img className="w-1/3 m-1 mb-3 mx-auto h-auto" alt="quick fix" src={quickFix}></img>
        <Text text='Lo errores se muestran en la parte superior de la bandeja, seguidos por las advertencias.'/>
        <Text text='Si no existen errores, la bandeja se puede minimizar.'/>
      </div>
    </div>

  )
}

export default Instructions
