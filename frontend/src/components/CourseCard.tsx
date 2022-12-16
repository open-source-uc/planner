import { useState, useRef } from 'react'
import { useDrag, useDrop } from 'react-dnd'
import type { Course } from '../lib/types'
const CourseCard = (props: { course: Course, handleMove: Function }): JSX.Element => {
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
  const [, drop] = useDrop(() => ({
    accept: 'card',
    drop (course: Course) {
      props.handleMove(course)
    }
  }))

  drag(drop(ref))
  return collected.isDragging
    ? (
    <div ref={dragPreview}>
    </div>
      )
    : (
    <div ref={ref} className={'bg-plan-comun card'} >
      <div className='text-center'>{course.ramo.sigla}</div>
    </div>
      )
}

export default CourseCard
