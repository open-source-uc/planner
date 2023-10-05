import { useState, useEffect } from 'react'

const useContextMenu = (): { clicked: boolean, setClicked: Function, points: { x: number, y: number }, setPoints: Function } => {
  const [clicked, setClicked] = useState(false)
  const [points, setPoints] = useState({
    x: 0,
    y: 0
  })
  useEffect(() => {
    const handleClick = (): void => { setClicked(false) }
    document.addEventListener('click', handleClick)
    return () => {
      document.removeEventListener('click', handleClick)
    }
  }, [])
  return {
    clicked,
    setClicked,
    points,
    setPoints
  }
}
export default useContextMenu
