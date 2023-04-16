import Home from './pages/Home'
import Planner from './pages/planner/Planner'
import Layout from './layout/Layout'
import UserPage from './pages/user/UserPage'
import Logout from './pages/Logout'
import Error403 from './pages/Error403'
import { DefaultService } from './client'

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
  await DefaultService.checkAuth().catch(err => {
    if (err.status === 401) {
      throw new Error(err.message)
    }
    if (err.status === 403) {
      window.location.href = '/403'
    }
  })
}

function onAuthenticationError (): void {
  window.location.href = `${import.meta.env.VITE_BASE_API_URL as string}/auth/login`
  localStorage.removeItem('access-token')
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
  path: '/planner/',
  component: Planner,
  loader: () => ({
    plannerId: null
  })
})

const getPlannerRoute = newPlannerRoute.createRoute({
  path: '$plannerId',
  loader: async ({ params }) => ({
    plannerId: params.plannerId
  }),
  beforeLoad: authenticateRoute,
  onLoadError: onAuthenticationError
})

const logoutRoute = rootRoute.createRoute({
  path: '/logout',
  component: Logout
})

const routeConfig = rootRoute.addChildren([homeRoute, userPageRoute, error403, newPlannerRoute.addChildren([getPlannerRoute]), logoutRoute])

export const router = createReactRouter({
  routeConfig
})

declare module '@tanstack/react-router' {
  interface RegisterRouter {
    router: typeof router
  }
}

export default router
