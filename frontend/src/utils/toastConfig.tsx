import { toast } from 'react-toastify'

const isPlannerRedirection = (data: any): data is { planId: string } => {
  return data.planId !== undefined
}

export function toastConfig (): void {
  toast.onChange((payload: any) => {
    if (payload.status === 'removed' && payload.type === toast.TYPE.ERROR && payload.id === 'ERROR401') {
      window.location.href = `${import.meta.env.VITE_BASE_API_URL as string}/auth/login`
      localStorage.removeItem('access-token')
    } else if (payload.status === 'removed' && payload.type === toast.TYPE.SUCCESS && payload.id === 'newPlanSaved') {
      const data = payload.data
      if (isPlannerRedirection(data)) {
        window.location.href = `/planner/${data.planId}`
      }
    }
  })
}
