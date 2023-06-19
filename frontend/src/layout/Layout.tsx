import { Outlet } from '@tanstack/react-router'
import Footer from './Footer'
import Navbar from './Navbar'
import { ToastContainer } from 'react-toastify'
function Layout (): JSX.Element {
  return (
      <div className="h-screen flex flex-col overflow-hidden">
        <Navbar/>
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
        <Outlet/>
        <Footer/>
      </div>
  )
}

export default Layout
