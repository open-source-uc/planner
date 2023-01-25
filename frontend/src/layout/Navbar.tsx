
import { Link } from '@tanstack/react-router'
import router from '../router'
import { useAuth } from '../contexts/auth.context'

function Navbar (): JSX.Element {
  const authState = useAuth()

  return (

<nav className="bg-gray border-slate-200 px-2 sm:px-4 py-2.5 rounded border">
  <div className="container flex flex-wrap items-center justify-between mx-auto">
   <span className="self-center text-xl font-semibold whitespace-nowrap text-blue-800">PanguiPath</span>
    <button data-collapse-toggle="navbar-default" type="button" className="inline-flex items-center p-2 ml-3 text-sm text-gray-500 rounded-lg md:hidden hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-200" aria-controls="navbar-default" aria-expanded="false">
 <span className="sr-only">Abrir menú principal</span>
 <svg className="w-6 h-6" aria-hidden="true" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd"></path></svg>
    </button>
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
   {authState?.user == null ? <a href="/api/auth/login" className="block py-2 pl-3 pr-4 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0">Iniciar sesión</a> : <Link to="/logout" className="block py-2 pl-3 pr-4 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0">Cerrar sesión</Link>}
   </li>
 </ul>
    </div>
  </div>
</nav>

  )
}

export default Navbar
