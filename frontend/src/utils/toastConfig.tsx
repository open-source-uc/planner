import { toast } from 'react-toastify'
import { loadEnvWithDefault } from './env'

export function toastConfig (): void {
  const env = loadEnvWithDefault()

  toast.onChange((payload: any) => {
    if (payload.status === 'removed' && payload.type === toast.TYPE.ERROR && payload.id === 'ERROR401') {
      window.location.href = `${env.VITE_BASE_API_URL as string}/user/login`
      localStorage.removeItem('access-token')
    } else if (payload.status === 'removed' && payload.type === toast.TYPE.ERROR && payload.id === 'ERROR403') {
      window.location.href = '/logout'
      localStorage.removeItem('access-token')
    }
  })
}
