import { useState } from 'react'
import reactLogo from './assets/react.svg'
import './App.css'
import Consts from './Consts'

const params = new URLSearchParams(window.location.search)
let jwt = params.get('jwt')
if (jwt === null) {
  jwt = localStorage.getItem('login-jwt')
} else {
  localStorage.setItem('login-jwt', jwt)
}

if (jwt === null) {
  console.log('no jwt available')
} else {
  console.log(`jwt = ${jwt}`)
}

async function getCourses(): Promise<void> {
  const req = new Request(Consts.backendUrl.getDoneCourses)
  const res = await fetch(req)
  console.log(res)
}

function App(): JSX.Element {
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
      <a href={Consts.backendUrl.login}>Login</a>
      <button onClick={() => { getCourses().catch(err => console.error(err)) }}>Get my done courses</button>
    </div >
  )
}

export default App
