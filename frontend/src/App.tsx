import { useState } from 'react'
import reactLogo from './assets/react.svg'
import './App.css'
import paths from './paths'
import { checkAuth } from './api'

function App (): JSX.Element {
  const [count, setCount] = useState(0)

  return (
    <div className="App">
      <div>
        <a href="https://vitejs.dev" target="_blank" rel="noreferrer">
          <img src="/vite.svg" className="logo" alt="Vite logo" />
        </a>
        <a href="https://reactjs.org" target="_blank" rel="noreferrer">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>Vite + React</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
        <p>
          Edit <code>src/App.tsx</code> and save to test HMR
        </p>
      </div>
      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
      <a href={paths.backend.prefix + paths.backend.authenticate}>Login</a>
      <p>Authenticated: <span id='auth-status'>...</span></p>
    </div >
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
