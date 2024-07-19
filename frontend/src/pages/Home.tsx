import { Link } from '@tanstack/react-router'
// import { useAuth } from '../contexts/auth.context'
import demoGif from '../assets/demo_gif.gif'
import AlertModal from '../components/AlertModal'
import { useState } from 'react'
import { useAuth } from '../contexts/auth.context'
import { hideLogin } from '../utils/featureFlags'

const AlertMobileUssage = (): JSX.Element => {
  return (
    <div className='lg:hidden mx-auto w-[90%] my-4 mb-8 text-lg text-center bg-red-100 border-red-600 text-red-950 p-2 border-2 rounded max-w-lg'>
      <span className='font-bold'>Importante:</span> La plataforma aún no está optimizada para pantallas pequeñas. Te recomendamos usar un computador.
    </div>
  )
}

const Home = (): JSX.Element => {
  const authState = useAuth()
  const [disclaimerIsOpen, setDisclaimerIsOpen] = useState(true)

  const loggedIn = authState?.user != null
  const isMod = authState?.isMod === true
  const isAdmin = authState?.isAdmin === true
  return (
    <div className="bg-gradient-to-b from-blue-500 h-full">
      <AlertModal
        title={'Importante'}
        isOpen={disclaimerIsOpen}
        close={() => {
          setDisclaimerIsOpen(false)
        }}
        disclaimer={true}
      >
        <div className="prose text-md">
          <p className="mb-0">
            Planner puede cometer errores.
          </p>
          <ul className="list-disc pl-5 mt-0">
            <li>
              Las mallas validadas pueden tener errores.
              <ul>
                <li>Revisa manualmente que la malla haga sentido.</li>
                <li>Recuerda que SIDING es la referencia oficial.</li>
              </ul>
            </li>
            {
              hideLogin &&
                (<li>
                Por ahora, el <span className='font-bold'>login UC no está funcionando</span>, así que
                debes <a href="https://github.com/open-source-uc/planner/pull/276#issue-1808769979" target="_blank" rel="noopener noreferrer">
                  ingresar tus cursos manualmente en el modo invitado
                </a>.
              </li>)
            }
          </ul>
        </div>
      </AlertModal>
      <div className="max-w-3xl mx-auto mt-8 center">
        <AlertMobileUssage />
        <h1 className="text-white text-center text-4xl mb-8 font-medium">
          Bienvenido a Mallas ING, el lugar donde puedes planificar tu
          carrera universitaria
        </h1>
        <div className="flex justify-evenly">
          {
          hideLogin
            ? (
            <Link to="/planner/new">
            <button className="rounded-lg py-2 px-4 bg-blue-800 text-white">
              Planificar Malla
            </button>
          </Link>
              )
            : (loggedIn
                ? <>{isMod && <Link to="/mod/users">
                    <button className="rounded-lg py-2 px-4 bg-blue-800 text-white">
                      Buscar Mallas de estudiantes
                    </button>
                  </Link>}
                  {isAdmin && <Link to="/admin/mods">
                    <button className="rounded-lg py-2 px-4 bg-blue-800 text-white">
                      Gestionar Moderadores
                    </button>
                  </Link>}
                  {!isMod && !isAdmin && <Link to="/user">
                      <button className="rounded-lg py-2 px-4 bg-blue-800 text-white">
                        Mis mallas
                      </button>
                    </Link>
                  }</>
                : (<>
              <a href="/api/user/login">
                <button className="rounded-lg py-2 px-4 bg-blue-800 text-white">
                  Iniciar sesión
                </button>
              </a>
              <Link to="/planner/new">
                <button className="rounded-lg py-2 px-4 bg-blue-800 text-white">
                  Continuar como invitado
                </button>
              </Link>
              </>
                  ))}
        </div>
      </div>
      <img className="p-2 mx-auto max-w-2xl w-full aspect-auto" alt="demo" src={demoGif}></img>
    </div>
  )
}

export default Home
