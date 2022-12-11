import Home from './pages/Home'
import Planner from './pages/Planner'

import Layout from './layout/Layout'

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

const plannerRoute = rootRoute.createRoute({
  path: '/planner',
  component: Planner
})

const routeConfig = rootRoute.addChildren([homeRoute, plannerRoute])

export const router = createReactRouter({
  routeConfig
})

declare module '@tanstack/react-router' {
  interface RegisterRouter {
    router: typeof router
  }
}

export default router
