import { Link, useRouter } from '@tanstack/react-router'
import { useAuth } from '../contexts/auth.context'
import { memo } from 'react'
import { hideLogin } from '../utils/featureFlags'

function Navbar (): JSX.Element {
  const authState = useAuth()
  const router = useRouter()
  const loggedIn = authState?.user != null
  const isMod = authState?.isMod === true
  const isAdmin = authState?.isAdmin === true
  return (
    <nav className="bg-gray border-slate-200 px-2 sm:px-4 py-2.5 rounded border">
      <div className="container flex flex-wrap items-center justify-between mx-auto">
        <Link to="/" className="self-center">
          <img src="/logo.png" className="h-20" alt="Logo" />
        </Link>

        <div className="hidden w-full md:block md:w-auto" id="navbar-default">
          <ul className="flex flex-col p-4 mt-4 border border-gray-100 rounded-lg bg-gray-50 md:flex-row md:space-x-8 md:mt-0 md:text-sm md:font-medium md:border-0 md:bg-white ">
            <li>
              <Link
                to="/"
                className={`block py-2 pl-3 pr-40 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0 ${
                  router.state.currentLocation.pathname === '/'
                    ? 'text-white bg-blue-700 md:bg-transparent md:text-blue-700'
                    : ''
                }`}
              >
                Inicio
              </Link>
            </li>
            {!isMod && !isAdmin &&
            <li>
              <Link
                to="/planner/new"
                className={`block py-2 pl-3 pr-40 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0 ${
                  router.state.currentLocation.pathname === '/planner/new'
                    ? 'text-white bg-blue-700 md:bg-transparent md:text-blue-700'
                    : ''
                }`}
              >
                Planificar
              </Link>
            </li>
            }
            {hideLogin
              ? null
              : loggedIn
                ? (
              <>
                <li>
                  {isMod && <Link
                    to="/mod/users"
                    className={`block py-2 pl-3 pr-40 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0 ${
                      router.state.currentLocation.pathname === '/mod/users'
                        ? 'text-white bg-blue-700 md:bg-transparent md:text-blue-700'
                        : ''
                    }`}
                  >
                    Buscar mallas
                  </Link>
                  }{isAdmin && <Link
                    to="/admin/mods"
                    className={`block py-2 pl-3 pr-40 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0 ${
                      router.state.currentLocation.pathname === '/admin/mods'
                        ? 'text-white bg-blue-700 md:bg-transparent md:text-blue-700'
                        : ''
                    }`}
                  >
                    Gestionar Mods
                  </Link>
                  }
                  {!isMod && !isAdmin && <Link
                    to="/user"
                    className={`block py-2 pl-3 pr-40 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0 ${
                      router.state.currentLocation.pathname === '/user'
                        ? 'text-white bg-blue-700 md:bg-transparent md:text-blue-700'
                        : ''
                    }`}
                  >
                    Mis mallas
                  </Link>}
                </li>
                <li>
                  <Link
                    to="/logout"
                    className="block py-2 pl-3 pr-4 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0"
                  >
                    Cerrar sesión
                  </Link>
                </li>
              </>
                  )
                : (
              <li>
                <a
                  href="/api/user/login"
                  className="block py-2 pl-3 pr-4 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-blue-700 md:p-0"
                >
                  Iniciar sesión
                </a>
              </li>
                  )}
          </ul>
        </div>
      </div>
    </nav>

  )
}

export default memo(Navbar)
