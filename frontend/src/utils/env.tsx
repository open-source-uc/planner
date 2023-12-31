import dotenv from 'dotenv'
import fs from 'fs'

export const loadEnvWithDefault = () => {
  const defaultEnv = dotenv.parse(fs.readFileSync('.env.default'))
  const env = dotenv.config({ path: ".env" }).parsed

  // Combine default and environment-specific env variables
  return { ...defaultEnv, ...env }
}
