import Axios from 'axios'
import dotenv from 'dotenv'
import fs from 'fs'

const loadEnvWithDefault = () => {
  const defaultEnv = dotenv.parse(fs.readFileSync('.env.default'))
  const env = dotenv.config({ path: ".env" }).parsed

  // Combine default and environment-specific env variables
  return { ...defaultEnv, ...env }
}

const env = loadEnvWithDefault()

const axios = Axios.create({
  baseURL: env.VITE_BASE_API_URL,
})

// Inject the token into the request header
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('access-token')
  if (token != null) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// The exported axios can be used to make requests
// to the API without worrying about base URLs or using the token
// However it is recommended to use the generated client instead
export default axios
