const Logout = (): JSX.Element => {
  // Clear token from local storage
  localStorage.removeItem('access-token')

  // eslint-disable-next-line @typescript-eslint/strict-boolean-expressions
  const casURL: string = import.meta.env.VITE_CAS_SERVER_URL || 'https://sso.uc.cl/cas/'
  console.assert(casURL, 'VITE_CAS_SERVER_URL environment variable not set during build')

  // Redirect to SSO logout URL
  const ssoLogoutURL = new URL('logout', casURL).toString()
  window.location.href = ssoLogoutURL

  return <div className="mx-auto my-auto">
    <h2 className="font-bold text-2xl">
    Cerrando sesión... &nbsp; 👋
    </h2>
  </div>
}

export default Logout
