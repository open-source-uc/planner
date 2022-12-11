import Axios from 'axios'

const axios = Axios.create({
  baseURL: import.meta.env.VITE_BASE_API_URL
})

// Inject the token into the request header
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('access-token')
  if (config.headers === undefined) {
    config.headers = {}
  }
  if (token != null) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// The exported axios can be used to make requests
// to the API without worrying about base URLs or using the token
// However it is recommended to use the generated client instead
export default axios
