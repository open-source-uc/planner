import Home from './pages/Home'
import Planner from './pages/planner/Planner'
import Layout from './layout/Layout'
import UserPage from './pages/user/UserPage'
import UserViewer from './pages/mod/userViewer'
import ModsViewer from './pages/admin/modsViewer'
import Logout from './pages/Logout'
import Error403 from './pages/errors/Error403'
import Error404 from './pages/errors/Error404'
import { DefaultService, type ApiError } from './client'
import { toast } from 'react-toastify'
import {
  ReactRouter,
  RootRoute, Route
} from '@tanstack/react-router'
import { isApiError } from './pages/planner/utils/Types'

const rootRoute = new RootRoute({
  component: Layout
})

const homeRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/',
  component: Home
})

async function adminRoute (): Promise<void> {
  try {
    await DefaultService.checkAdmin()
  } catch (err) {
    if (isApiError(err)) {
      authError(err)
    }
    throw err
  }
}

async function modRoute (): Promise<void> {
  try {
    await DefaultService.checkMod()
  } catch (err) {
    if (isApiError(err)) {
      authError(err)
    }
    throw err
  }
}
async function authenticateRoute (): Promise<void> {
  try {
    await DefaultService.checkAuth()
  } catch (err) {
    if (isApiError(err)) {
      authError(err)
    }
    throw err
  }
}
function authError (err: ApiError): void {
  if (err.status === 403) {
    window.location.href = '/403'
  }
  if (err.status === 401) {
    console.log('token invalid or expired, loading re-login page')
    toast.error('Tu session a expirado. Redireccionando a pagina de inicio de sesion...', {
      toastId: 'ERROR401'
    })
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
  beforeLoad: authenticateRoute
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
  validateSearch: (params) => ({
    plannerId: params.plannerId
  })
})

const newPlannerForModRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/mod/planner/new/$userRut',
  component: Planner,
  beforeLoad: modRoute
})

const viewPlannerForModRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/mod/planner/$userRut/$plannerId',
  beforeLoad: modRoute,
  component: Planner
})

const UserViewerForMod = new Route({
  getParentRoute: () => rootRoute,
  path: '/mod/users',
  beforeLoad: modRoute,
  validateSearch: (search: Record<string, unknown>): { studentRut: string } => {
    return {
      studentRut: typeof search?.studentRut === 'number' ? search.studentRut.toString() : typeof search?.studentRut === 'string' ? search.studentRut : ''
    }
  },
  component: UserViewer
})

const ModsViewerForAdmin = new Route({
  getParentRoute: () => rootRoute,
  path: '/admin/mods',
  beforeLoad: adminRoute,
  component: ModsViewer
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

const routeTree = rootRoute.addChildren([homeRoute, userPageRoute, error403, newPlannerRoute, getPlannerRoute, ModsViewerForAdmin, UserViewerForMod, newPlannerForModRoute, viewPlannerForModRoute, logoutRoute, error404])

export const router = new ReactRouter({
  routeTree,
  context: {
    isMod: false
  }
})

declare module '@tanstack/react-router'{
  interface RegisterRouter {
    router: typeof router
  }
}

export default router
