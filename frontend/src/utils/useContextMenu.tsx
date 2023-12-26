import { useState, useEffect, type MouseEventHandler } from 'react'

interface useContextMenuReturn {
  clicked: boolean
  points: { x: number, y: number }
  handleContextMenu: MouseEventHandler
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
    console.log(e)
    e.preventDefault()
    setClicked(true)
    setPoints({
      x: e.pageX,
      y: e.pageY
    })
    const courseCode = e.currentTarget.getAttribute('data-course-code')
    const courseInstance = e.currentTarget.getAttribute('data-course-instance')
    const courseIsEquiv = e.currentTarget.getAttribute('data-course-hasEquiv')
    const courseCredits = e.currentTarget.getAttribute('data-course-credits')

    if (courseCode != null && courseInstance != null && courseIsEquiv != null && courseCredits != null) {
      setCourseInfo({
        code: courseCode,
        instance: parseInt(courseInstance),
        isEquivalence: courseIsEquiv === 'true',
        credits: parseInt(courseCredits)
      })
    }
    console.log('Right Click', courseCode, courseInstance, e.pageX, e.pageY)
  }
  useEffect(() => {
    const handleClick = (): void => { setClicked(false) }
    document.addEventListener('click', handleClick)
    return () => {
      document.removeEventListener('click', handleClick)
    }
  }, [])
  return {
    clicked,
    points,
    courseInfo,
    handleContextMenu
  }
}
export default useContextMenu
