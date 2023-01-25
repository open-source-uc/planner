
import { Link } from '@tanstack/react-router'
import router from '../router'
import { useAuth } from '../contexts/auth.context'
import { ReactComponent as PanguiPath } from '../assets/PanguiPath.svg'

function Navbar (): JSX.Element {
  const authState = useAuth()

  return (
<nav className="bg-gray border-slate-200 px-2 sm:px-4 py-2.5 rounded border">
    <div className="container flex flex-wrap items-center justify-between mx-auto">
        <Link to="/" className="self-center"><PanguiPath className="h-20" /></Link>

        <div className="hidden w-full md:block md:w-auto" id="navbar-default">
            <ul className="flex flex-col p-4 mt-4 border border-gray-100 rounded-lg bg-gray-50 md:flex-row md:space-x-8 md:mt-0 md:text-sm md:font-medium md:border-0 md:bg-white ">
                <li>
                    <Link to="/" className={`block py-2 pl-3 pr-40 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0 ${router.matchRoute({ to: '/' }) ? 'text-white bg-blue-700 md:bg-transparent md:text-blue-700' : ''}`}>Inicio</Link>
                </li>
                <li>
                    <Link to="/planner" className={`block py-2 pl-3 pr-40 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0 ${router.matchRoute({ to: '/planner' }) ? 'text-white bg-blue-700 md:bg-transparent md:text-blue-700' : ''}`}>Nueva planificación</Link>
                </li>
                <li>
                    <Link to="/user" className={`block py-2 pl-3 pr-40 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0 ${router.matchRoute({ to: '/user' }) ? 'text-white bg-blue-700 md:bg-transparent md:text-blue-700' : ''}`}>Mis mallas</Link>
                </li>

                <li>
                    {authState?.user == null
                      ? <a href="/api/auth/login" className="block py-2 pl-3 pr-4 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0">Iniciar sesión</a>
                      : <Link to="/logout" className="block py-2 pl-3 pr-4 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0">Cerrar sesión</Link>}
                </li>
            </ul>
        </div>
    </div>
</nav>

  )
}

export default Navbar
