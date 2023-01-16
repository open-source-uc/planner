
import { Link } from '@tanstack/react-router'
import { useAuth } from '../contexts/auth.context'

function Navbar (): JSX.Element {
  const authState = useAuth()

  return (
    <nav className="gap-4 font-bold mx-auto max-w-sm mt-5">
      <ul>
        <li className="inline mr-4"><Link to="/">Inicio</Link></li>
        <li className="inline mr-4"><Link to="/user">User</Link></li>
        <li className="inline mr-4"><Link to="/planner">Planner</Link></li>
        {authState?.user == null
          ? <li className="inline mr-4"><a href="/api/auth/login">Log in</a></li>
          : <li className="inline mr-4"><Link to="/logout">Cerrar sesión</Link></li>
        }
      </ul>
    </nav>)
}

export default Navbar
