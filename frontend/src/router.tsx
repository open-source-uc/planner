import Home from './pages/Home'
import Planner from './pages/planner/Planner'
import Layout from './layout/Layout'
import UserPage from './pages/user/UserPage'
import Logout from './pages/Logout'
import Error403 from './pages/errors/Error403'
import Error404 from './pages/errors/Error404'
import { DefaultService, type ApiError } from './client'
import { toast } from 'react-toastify'
import {
  ReactRouter,
  RootRoute, Route
} from '@tanstack/react-router'

const rootRoute = new RootRoute({
  component: Layout
})

const homeRoute = new Route({
  getParentRoute: () => rootRoute,
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

const error403 = new Route({
  getParentRoute: () => rootRoute,
  path: '/403',
  component: Error403
})

const userPageRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/user',
  component: UserPage,
  beforeLoad: authenticateRoute,
  onLoadError: onAuthenticationError
})

const newPlannerRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/planner/new',
  component: Planner,
  validateSearch: () => ({
    plannerId: null
  })
})

const getPlannerRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/planner/$plannerId',
  component: Planner,
  beforeLoad: authenticateRoute,
  onLoadError: onAuthenticationError,
  validateSearch: (params) => ({
    plannerId: params.plannerId
  })
})

const logoutRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/logout',
  component: Logout
})

const error404 = new Route({
  getParentRoute: () => rootRoute,
  path: '*',
  component: Error404
})

const routeTree = rootRoute.addChildren([homeRoute, userPageRoute, error403, newPlannerRoute, getPlannerRoute, logoutRoute, error404])

export const router = new ReactRouter({
  routeTree
})

declare module '@tanstack/router'{
  interface RegisterRouter {
    router: typeof router
  }
}

export default router
