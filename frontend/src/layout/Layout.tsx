import { Outlet } from '@tanstack/react-router'
import Footer from './Footer'
import Navbar from './Navbar'
import { ToastContainer } from 'react-toastify'

function Layout (): JSX.Element {
  return (
    <div className="flex flex-col overflow-hidden">
    <div className="flex flex-col overflow-hidden h-screen">
      <Navbar />
      <ToastContainer
        position="top-center"
        autoClose={2500}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick={true}
        draggable={false}
        pauseOnFocusLoss={false}
        pauseOnHover={false}
        rtl={false}
        theme="light"
      />
      <Outlet />
    </div>
    <hr/>
    <Footer />
  </div>
  )
}

export default Layout
