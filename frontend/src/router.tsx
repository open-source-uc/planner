import Home from './pages/Home'
import Planner from './pages/planner/Planner'
import Layout from './layout/Layout'
import UserPage from './pages/user/UserPage'
import Logout from './pages/Logout'
import Error403 from './pages/errors/Error403'
import Error404 from './pages/errors/Error404'
import { DefaultService, ApiError } from './client'
import { toast } from 'react-toastify'
import {
  createReactRouter,
  createRouteConfig
} from '@tanstack/react-router'

const rootRoute = createRouteConfig({
  component: Layout
})

const homeRoute = rootRoute.createRoute({
  path: '/',
  component: Home
})

async function authenticateRoute (): Promise<void> {
  await DefaultService.checkAuth()
}

function onAuthenticationError (err: ApiError): void {
  if (err.status === 401) {
    console.log('token invalid or expired, loading re-login page')
    toast.error('Tu session a expirado. Redireccionando a pagina de inicio de sesion...', {
      toastId: 'ERROR401'
    })
  }
  if (err.status === 403) {
    window.location.href = '/403'
  }
}

const error403 = rootRoute.createRoute({
  path: '/403',
  component: Error403
})

const userPageRoute = rootRoute.createRoute({
  path: '/user',
  component: UserPage,
  beforeLoad: authenticateRoute,
  onLoadError: onAuthenticationError
})

const newPlannerRoute = rootRoute.createRoute({
  path: '/planner/new',
  component: Planner,
  loader: () => ({
    plannerId: null
  })
})

const getPlannerRoute = rootRoute.createRoute({
  path: '/planner/$plannerId',
  loader: async ({ params }) => ({
    plannerId: params.plannerId
  }),
  component: Planner,
  beforeLoad: authenticateRoute,
  onLoadError: onAuthenticationError
})

const logoutRoute = rootRoute.createRoute({
  path: '/logout',
  component: Logout
})

const error404 = rootRoute.createRoute({
  path: '*',
  component: Error404
})

const routeConfig = rootRoute.addChildren([homeRoute, userPageRoute, error403, newPlannerRoute, getPlannerRoute, logoutRoute, error404])

export const router = createReactRouter({
  routeConfig
})

declare module '@tanstack/react-router' {
  interface RegisterRouter {
    router: typeof router
  }
}

export default router
