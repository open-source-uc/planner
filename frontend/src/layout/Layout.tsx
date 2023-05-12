import { Outlet } from '@tanstack/react-router'
import Footer from './Footer'
import Navbar from './Navbar'
import { ToastContainer, toast } from 'react-toastify'

const isPlannerRedirection = (data: any): data is { planId: string } => {
  return data.planId !== undefined
}

toast.onChange(payload => {
  if (payload.status === 'removed' && payload.type === toast.TYPE.ERROR && payload.id === 'ERROR401') {
    window.location.href = `${import.meta.env.VITE_BASE_API_URL as string}/auth/login`
    localStorage.removeItem('access-token')
  } else if (payload.status === 'removed' && payload.type === toast.TYPE.SUCCESS && payload.id === 'newPlanSaved') {
    if (isPlannerRedirection(payload.data)) {
      window.location.href = `/planner/${payload.data.planId}`
    }
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
