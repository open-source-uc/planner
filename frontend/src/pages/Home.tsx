import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/auth.context'
import { DefaultService, PostCreateInput } from '../client'

const Home = (): JSX.Element => {
  const authState = useAuth()
  const [posts, setPosts] = useState<PostCreateInput[]>([])

  useEffect(() => {
    const getPosts = async (): Promise<void> => {
      const posts = await DefaultService.getPosts()
      setPosts(posts)
    }
    void getPosts()
  }, [])

  return (
        <div className="max-w-md mx-auto mt-8 prose">
            <h2>Inicio</h2>
            {authState?.user != null && (<p>Has iniciado sesión.</p>)}
            <pre>
                {authState != null && JSON.stringify(authState, null, 2)}
            </pre>
            <p>Prueba del cliente (lista de posts):</p>
            {posts.map((post: PostCreateInput) => (
                <div key={post.id}>
                    <h3>{post.title}</h3>
                </div>
            ))}
        </div>
  )
}

export default Home
