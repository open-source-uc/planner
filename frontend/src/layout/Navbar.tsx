
import { Link } from '@tanstack/react-router'
import { useAuth } from '../contexts/auth.context'

function Navbar (): JSX.Element {
  const authState = useAuth()

  return (
    <nav className="gap-4 font-bold mx-5 my-3 flex justify-between items-center">
      <ul className="flex items-center">
        <li className="inline mr-4"><Link to="/">Inicio</Link></li>
      </ul>
      <ul className="flex items-center">
        <li className="inline mr-4 justify-end"><Link to="/planner">Crear Malla</Link></li>
        <li className="inline mr-4 justify-end">
        {authState?.user == null
          ? (<a href="/api/auth/login">Log in</a>)
          : (<>
            <li className="inline mr-4"><Link to="/user">User</Link></li>
            <Link to="/logout">Cerrar sesión</Link>
          </>)}
        </li>
      </ul>

    </nav>)
}

export default Navbar
