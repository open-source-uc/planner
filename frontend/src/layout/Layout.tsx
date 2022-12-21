import { Outlet } from '@tanstack/react-router'
import Footer from './Footer'
import Navbar from './Navbar'

function Layout (): JSX.Element {
  return (
      <div className="h-screen flex flex-col overflow-hidden">
        <Navbar/>
        <Outlet/>
        <Footer/>
      </div>
  )
}

export default Layout
