import { Outlet } from '@tanstack/react-router'
import Footer from './Footer'
import Navbar from './Navbar'
import { ToastContainer, toast } from 'react-toastify'

toast.onChange(payload => {
  if (payload.status === 'removed' && payload.type === toast.TYPE.ERROR) {
    window.location.href = `${import.meta.env.VITE_BASE_API_URL as string}/auth/login`
    localStorage.removeItem('access-token')
  }
})

function Layout (): JSX.Element {
  return (
      <div className="h-screen flex flex-col overflow-hidden">
        <Navbar/>
        <ToastContainer
          position="top-center"
          autoClose={3000}
          hideProgressBar={false}
          newestOnTop={false}
          closeOnClick
          rtl={false}
          theme="light"
        />
        <Outlet/>
        <Footer/>
      </div>
  )
}

export default Layout
