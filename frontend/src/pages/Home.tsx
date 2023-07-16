import { Link } from '@tanstack/react-router'
// import { useAuth } from '../contexts/auth.context'
import demoGif from '../assets/demo_gif.gif'
import AlertModal from '../components/AlertModal'
import { useState } from 'react'

const alphaDisclaimer = `Esta aplicación se encuentra en una fase de desarrollo alpha, por lo tanto, es fundamental tener en cuenta que la información mostrada puede no ser completamente precisa.
Esto incluye posibles discrepancias en la verificacion de los requisitos de algunos ramos, junto a errores en la generacion y verificacion de distintas mallas curriculares de cada plan de estudio. 
Por favor, verifique cualquier planificación con la información oficial proporcionada por la universidad para garantizar su exactitud.`

const Home = (): JSX.Element => {
  // const authState = useAuth()
  const [disclaimerIsOpen, setDisclaimerIsOpen] = useState(true)

  return (
    <div className='bg-gradient-to-b from-blue-500 h-full'>
      <AlertModal title={'IMPORTANTE: POR FAVOR, LEA ATENTAMENTE'} desc={alphaDisclaimer} isOpen={disclaimerIsOpen} close={() => { setDisclaimerIsOpen(false) }} disclaimer={true}/>
      <div className="max-w-3xl mx-auto mt-8 prose center">
          <h1 className='text-white text-center font-medium'>Bienvenido a PanguiPath, el lugar donde puedes planificar tu carrera universitaria</h1>
          <div className='flex justify-evenly'><Link to="/planner/new"><button className='rounded-lg py-2 px-4 bg-blue-800 text-white'>Planificar Malla</button></Link></div>
                {
                /* authState?.user != null
                  ? (<div className='flex justify-evenly'><Link to="/user"><button className='rounded-lg py-2 px-4 bg-blue-800 text-white'>Mis mallas</button></Link></div>)
                  : (<div className='flex justify-evenly'><a href="/api/user/login"><button className='rounded-lg py-2 px-4 bg-blue-800 text-white'>Iniciar sesión</button></a><Link to="/planner/new"><button className='rounded-lg py-2 px-4 bg-blue-800 text-white'>Continuar como invitado</button></Link></div>)}
                */}
            </div>
      <img className="w-auto m-5 mx-auto h-3/5" alt="demo" src={demoGif}></img>
    </div>
  )
}

export default Home
