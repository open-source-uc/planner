import { Link } from '@tanstack/router'
import { useAuth } from '../contexts/auth.context'
import demoGif from '../assets/demo_gif.gif'

const Home = (): JSX.Element => {
  const authState = useAuth()

  return (
    <div className='bg-gradient-to-b from-blue-500 h-full'>
      <div className="max-w-3xl mx-auto mt-8 prose center">
          <h1 className='text-white text-center font-medium'>Bienvenido a PanguiPath, el lugar donde puedes planificar tu carrera universitaria</h1>
          {authState?.user != null
            ? (<div className='flex justify-evenly'><Link to="/user"><button className='rounded-lg py-2 px-4 bg-blue-800 text-white'>Mis mallas</button></Link></div>)
            : (<div className='flex justify-evenly'><a href="/api/auth/login"><button className='rounded-lg py-2 px-4 bg-blue-800 text-white'>Iniciar sesión</button></a><Link to="/planner/new"><button className='rounded-lg py-2 px-4 bg-blue-800 text-white'>Continuar como invitado</button></Link></div>)}
          {/* <pre>
              {authState != null && JSON.stringify(authState, null, 2)}
          </pre> */}
      </div>
      <img className="w-auto m-5 mx-auto h-3/5" alt="demo" src={demoGif}></img>
    </div>
  )
}

export default Home
