import paths from './paths'
import { checkAuth } from './api'

function App (): JSX.Element {
  return (
      <div className='mx-auto my-auto max-w-20'>
        <a href={paths.backend.prefix + paths.backend.authenticate}>Login</a>
        <p>Authenticated: <span id='auth-status'>...</span></p>
      </div>
  )
}

checkAuth().then(ok => {
  const elem = document.getElementById('auth-status')
  if (elem !== null) elem.innerText = ok.toString()
}).catch(err => {
  const elem = document.getElementById('auth-status')
  if (elem !== null) elem.innerText = err.toString
})

export default App
