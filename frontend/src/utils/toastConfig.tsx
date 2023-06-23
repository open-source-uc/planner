import { toast } from 'react-toastify'

export function toastConfig (): void {
  toast.onChange((payload: any) => {
    if (payload.status === 'removed' && payload.type === toast.TYPE.ERROR && payload.id === 'ERROR401') {
      window.location.href = `${import.meta.env.VITE_BASE_API_URL as string}/auth/login`
      localStorage.removeItem('access-token')
    }
  })
}
