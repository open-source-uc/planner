import { useRef } from 'react'
import { useDrag, useDrop } from 'react-dnd'
import type { Course } from '../lib/types'

const CourseCard = ({ course, isDragging, handleMove, remCourse }: { course: any, isDragging: Function, handleMove: Function, remCourse: Function }): JSX.Element => {
  const ref = useRef(null)
  const [collected = { isDragging: false }, drag] = useDrag(
    () => ({
      type: 'card',

      item: () => {
        isDragging(true)
        return { course }
      },
      end () {
        isDragging(false)
      },
      // call startMove when the drag starts
      collect (monitor) {
        return {
          isDragging: monitor.isDragging()
        }
      }
    })
  )
  const [dropProps, drop] = useDrop(() => ({
    accept: 'card',
    drop (course: Course) {
      handleMove(course)
    },
    collect: monitor => ({
      isOver: !!monitor.isOver(),
      canDrop: !!monitor.canDrop(),
      item: monitor.getItem()
    })
  }))
  drag(drop(ref))
  return (
    <>
    <div ref={ref} draggable={true} className={`px-2 ${!collected.isDragging ? 'pb-3' : ''}`}>
      {dropProps.isOver
        ? <div className={'bg-place-holder card'} />
        : <>{!collected.isDragging && <div className={'bg-plan-comun card relative group flex justify-center'}>
          <button className='absolute top-0 right-2 hidden group-hover:inline' onClick={() => remCourse()}>x
          </button>
          <div className='flex items-center justify-center text-center'>{course.code}</div>
      </div>}
      </>}
    </div>
    {
      dropProps.isOver && <div className={'px-2 pb-3'}>
      <div className={'bg-plan-comun card relative'}>
        <div className='text-center'>{course.code}</div>
      </div>
    </div>
    }
    </>
  )
}

export default CourseCard
