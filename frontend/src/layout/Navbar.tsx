import { Link, useRouter } from '@tanstack/react-router'
import { useAuth } from '../contexts/auth.context'
import { memo } from 'react'
import { hideLogin } from '../utils/featureFlags'

function Navbar (): JSX.Element {
  return (
    <nav className="bg-gray border-slate-200 px-2 sm:px-4 py-2.5 rounded border">
      <div className="container flex flex-wrap items-center justify-between mx-auto">
        <Link to="/" className="self-center">
          <img src="/logo.png" className="h-20" alt="Logo" />
        </Link>
      </div>
    </nav>

  )
}

export default memo(Navbar)
