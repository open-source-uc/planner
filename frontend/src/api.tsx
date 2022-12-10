// Interaction with the backend.

import paths from './paths'

// If there is a token on the URL, we have just been redirected from the authentication page
// Store the token in localStorage
const params = new URLSearchParams(window.location.search)
let accessToken: string | null = params.get('token')
if (accessToken === null) {
  accessToken = localStorage.getItem('access-token')
} else {
  // Store the token in localStorage and clear it from the URL bar
  localStorage.setItem('access-token', accessToken)
  window.location.replace('/')
}

/**
 * Redirect to the authentication page for the user to log in.
 */
async function logIn (): Promise<void> {
  window.location.replace(paths.backend.prefix + paths.backend.authenticate)
  // Authentication won't be over until the page redirects and the user logs in
  // So basically, the entire page will die before authentication is done
  return await new Promise(() => {})
}

/**
 * Send a request, including authorization if available.
 * The request might be rejected if there is no authorization!
 */
async function sendRequest (path: string, method: string = 'get', body: any = null): Promise<Response> {
  const headers = new Headers()
  if (accessToken !== null) {
    headers.append('Authorization', 'Bearer ' + accessToken)
  }
  if (body !== null) {
    body = JSON.stringify(body)
  }
  return await fetch(paths.backend.prefix + path, { method, headers, body })
}

/**
 * Check if the user is currently authenticated.
 */
async function checkAuth (): Promise<boolean> {
  const res = await sendRequest(paths.backend.checkAuth)
  return res.status === 200
}

// DEBUG: Show token in console
// TODO: Remove this, possibly unsafe
if (accessToken === null) {
  console.log('no access token available (logged out)')
} else {
  console.log(`accessToken = ${accessToken}`)
}

export { logIn, checkAuth, sendRequest, accessToken }
