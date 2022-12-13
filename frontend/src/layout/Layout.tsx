import { Outlet } from '@tanstack/react-router'
import Footer from './Footer'
import Navbar from './Navbar'

function Layout (): JSX.Element {
  return (<>
        <Navbar/>
        <Outlet/>
        <Footer/>
        </>
  )
}

export default Layout
