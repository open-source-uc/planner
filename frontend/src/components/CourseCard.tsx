import { useState, useRef } from 'react'
import { useDrag } from 'react-dnd'
import type { Course } from '../lib/types'
const CourseCard = (props: { course: Course }): JSX.Element => {
  const [course] = useState(props.course)
  const ref = useRef(null)

  const [collected, drag, dragPreview] = useDrag(
    () => ({
      type: 'card',

      item: () => {
        return { course }
      },
      collect (monitor) {
        return {
          isDragging: monitor.isDragging()
        }
      }
    })
  )

  drag(ref)
  return collected.isDragging
    ? (
    <div ref={dragPreview} />
      )
    : (
    <div ref={ref} className={'bg-plan-comun card'} >
      <div className='text-center'>{course.ramo.sigla}</div>
    </div>
      )
}

export default CourseCard
