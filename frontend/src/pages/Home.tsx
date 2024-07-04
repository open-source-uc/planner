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
  return (
    <div className="bg-gradient-to-b from-blue-500 h-full">
      <div className="max-w-3xl mx-auto mt-8 center">
        <h1 className="text-white text-center text-4xl mb-8 font-medium">
          El Nuevo Planner se ha cambiado de hogar 🏠
          <br/>
          Dirígete a <a href="https://mallas.ing.uc.cl">mallas.ing.uc.cl</a>
        </h1>
      </div>
    </div>
  )
}

export default Home
