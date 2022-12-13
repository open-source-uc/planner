const Logout = (): JSX.Element => {
  // Clear token from local storage
  localStorage.removeItem('access-token')
  // Redirect to home page
  window.location.href = '/'
  return <p>Cerrando sesión...</p>
}

export default Logout
