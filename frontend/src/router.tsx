import Home from './pages/Home'
import Planner from './pages/planner/Planner'
import Layout from './layout/Layout'
import Logout from './pages/Logout'

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

function authenticateRoute (): void {
  const token = localStorage.getItem('access-token')
  if (token == null) {
    throw new Error('Not authenticated')
  }
}

function onAuthenticationError (): void {
  window.location.href = `${import.meta.env.VITE_BASE_API_URL as string}/auth/login`
}

const newPlannerRoute = rootRoute.createRoute({
  path: '/planner',
  component: Planner,
  loader: () => ({
    plannerId: null
  })
})

const getPlannerRoute = newPlannerRoute.createRoute({
  path: '/$plannerId',
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

const routeConfig = rootRoute.addChildren([homeRoute, newPlannerRoute.addChildren([getPlannerRoute]), logoutRoute])

export const router = createReactRouter({
  routeConfig
})

declare module '@tanstack/react-router' {
  interface RegisterRouter {
    router: typeof router
  }
}

export default router
