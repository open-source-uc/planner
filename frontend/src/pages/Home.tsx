
import { useAuth } from '../contexts/auth.context'

const Home = (): JSX.Element => {
  const authState = useAuth()

  return (
        <div className="max-w-md mx-auto mt-8 prose">
            <h2>Inicio</h2>
            {authState?.user != null && (<p>Has iniciado sesión.</p>)}
            <pre>
                {authState != null && JSON.stringify(authState, null, 2)}
            </pre>
        </div>
  )
}

export default Home
