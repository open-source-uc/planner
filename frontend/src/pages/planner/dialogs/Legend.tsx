import editBlackIcon from '../../../assets/editBlack.svg'
import currentBlackIcon from '../../../assets/currentBlack.svg'

const Description = ({ text }: { text: string }): JSX.Element => {
  return (
        <p className='ml-2 text-sm text-gray-500'>{text}</p>
  )
}

const SectionTitle = ({ text }: { text: string }): JSX.Element => {
  return (
        <h3 className='text-xl font-medium leading-normal mb-2 text-blue-800'>{text}</h3>
  )
}

const Legend = (): JSX.Element => {
  return (
    <div className="w-full flex">
        <div className="w-1/2">
            <SectionTitle text='Colores'/>
            <div className='m-3 card h-10 w-5/6 leading-8 group bg-block-PC'>Plan Común</div>
            <div className='m-3 card h-10 w-5/6 leading-8 group bg-block-M'>Major</div>
            <div className='m-3 card h-10 w-5/6 leading-8 group bg-block-m'>Minor</div>
            <div className='m-3 card h-10 w-5/6 leading-8 group bg-block-T'>Título</div>
            <div className='m-3 card h-10 w-5/6 leading-8 group bg-block-FG text-white'>Formación General</div>
            <div className='m-3 card h-10 w-5/6 leading-8 group bg-block-'>Curso no aporta al avance curricular</div>
            <div className='m-3 card h-10 w-5/6 leading-8 group bg-block- line-through'>Curso reprobado</div>
        </div>
        <div className="w-1/2">
            <SectionTitle text='Símbolos'/>
            <div className='flex my-3'><img className='w-5 text-center opacity-60' src={editBlackIcon} alt="Símbolo seleccionar curso" /><Description text={'Seleccionar curso'} /></div>
            <div className='flex my-3'><img className='w-5 text-center opacity-60' src={currentBlackIcon} alt="Símbolo curso en curso" /><Description text={'Curso en curso'} /></div>
            <div className='flex my-3'><div className="w-5 text-center">X</div><Description text={'Eliminar curso'} /></div>
            <div className='flex my-3'><div className='w-5 text-center'><span className="relative inline-flex rounded-full h-4 w-4 bg-yellow-400"></span></div><Description text={'Curso contiene advertencia(s)'} /></div>
            <div className='flex my-3'><div className='w-5 text-center'><span className="relative inline-flex rounded-full h-4 w-4 bg-red-400"></span></div><Description text={'Curso contiene error(es)'} /></div>
            <div className='flex my-3'><div className='w-5 text-center text-sm opacity-75'>PC</div><Description text={'Curso perteneciente al bloque Plan Común'} /></div>
            <div className='flex my-3'><div className='w-5 text-center text-sm opacity-75'>M</div><Description text={'Curso perteneciente al bloque Major'} /></div>
            <div className='flex my-3'><div className='w-5 text-center text-sm opacity-75'>m</div><Description text={'Curso perteneciente al bloque Minor'} /></div>
            <div className='flex my-3'><div className='w-5 text-center text-sm opacity-75'>T</div><Description text={'Curso perteneciente al bloque Título'} /></div>
            <div className='flex my-3'><div className='w-5 text-center text-sm opacity-75'>FG</div><Description text={'Curso perteneciente al bloque Formación General'} /></div>
            <div className='flex my-3'><div className="w-5 h-5 text-center leading-4 bg-block- rounded-md">+</div><Description text={'Agregar nuevo curso al semestre'} /></div>
            {/* <div className='flex my-3'><div className='text-center text-sm line-through'>Cálculo</div><Description text={'Curso reprobado'} /></div> */}
        </div>
    </div>
  )
}

export default Legend
