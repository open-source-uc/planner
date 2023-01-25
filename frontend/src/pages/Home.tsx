import { useAuth } from '../contexts/auth.context'
import demo from '../assets/demo.png'
import demoGif from '../assets/demo_gif.gif'

const Home = (): JSX.Element => {
  const authState = useAuth()

  return (
    <div className='bg-gradient-to-b from-blue-600 h-full'>
      <div className="max-w-xl mx-auto mt-8 prose cente">
          <h2 className='text-white'>Bienvenido a PanguiPath, el lugar donde puedes planificar tu carrera universitaria.</h2>
          {/* {authState?.user != null && (<p>Has iniciado sesión.</p>)} */}
          {authState?.user != null ? (<p>Has iniciado sesión.</p>) : (<p>iniciar sesión</p>)}
          {/* <pre>
              {authState != null && JSON.stringify(authState, null, 2)}
          </pre> */}
      </div>
      <img className="w-1/2 m-5 mx-auto" alt="demo" src={demoGif}></img>
    </div>

  )
}

export default Home
