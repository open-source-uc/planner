import { useState, useEffect, type MouseEventHandler } from 'react'

interface useContextMenuReturn {
  clicked: boolean
  points: { x: number, y: number }
  handleContextMenu: MouseEventHandler
  setClicked: Function
  courseInfo: { code: string, instance: number, credits: number, isEquivalence: boolean }
}

const useContextMenu = (): useContextMenuReturn => {
  const [clicked, setClicked] = useState(false)
  const [points, setPoints] = useState({
    x: 0,
    y: 0
  })

  const [courseInfo, setCourseInfo] = useState({
    code: '',
    instance: 0,
    isEquivalence: false,
    credits: 0
  })
  const handleContextMenu = (e: React.MouseEvent<HTMLDivElement>): void => {
    e.preventDefault()
    setClicked(true)
    setPoints({
      x: e.pageX,
      y: e.pageY
    })
    const courseCode = e.currentTarget.getAttribute('data-course-code')
    const courseInstance = e.currentTarget.getAttribute('data-course-instance')
    const courseIsEquiv = e.currentTarget.getAttribute('data-course-hasequiv')
    const courseCredits = e.currentTarget.getAttribute('data-course-credits')

    if (courseCode != null && courseInstance != null && courseIsEquiv != null && courseCredits != null) {
      setCourseInfo({
        code: courseCode,
        instance: parseInt(courseInstance),
        isEquivalence: courseIsEquiv === 'true',
        credits: parseInt(courseCredits)
      })
    }
    // console.log('Right Click', courseCode, courseInstance, e.pageX, e.pageY)
  }
  useEffect(() => {
    const handleClick = (e: MouseEvent): void => {
      const target = e.target as HTMLElement
      const contextMenu = document.getElementById('context-menu')
      if ((contextMenu != null) && !contextMenu.contains(target)) {
        setClicked(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => {
      document.removeEventListener('mousedown', handleClick)
    }
  }, [])
  return {
    clicked,
    setClicked,
    points,
    courseInfo,
    handleContextMenu
  }
}
export default useContextMenu
