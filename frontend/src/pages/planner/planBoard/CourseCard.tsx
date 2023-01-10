import { useRef } from 'react'
import { useDrag, useDrop } from 'react-dnd'
import { Course } from '../Planner'

interface CourseCardProps {
  course: Course
  isDragging: Function
  handleMove: Function
  remCourse: Function
}

const CourseCard = ({ course, isDragging, handleMove, remCourse }: CourseCardProps): JSX.Element => {
  const ref = useRef(null)
  const [collected = { isDragging: false }, drag] = useDrag(() => ({
    type: 'card',
    item: () => {
      isDragging(true)
      return { course }
    },
    end () {
      isDragging(false)
    },
    collect (monitor) {
      return { isDragging: monitor.isDragging() }
    }
  }))
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
        : <>{!collected.isDragging && <div className={'bg-plan-comun card group'}>
          <button className='absolute top-0 right-2 hidden group-hover:inline' onClick={() => remCourse()}>x</button>
          <div className='flex items-center justify-center text-center flex-col'>
            <div className='text-xs'>{ course.name }</div>
            <div className='text-[0.6rem] text-gray-600'>{course.code}</div>
          </div>
          <div className='absolute bottom-2 left-2 text-[0.5rem] text-gray-600'>{course.credits} creditos</div>
      </div>}
      </>}
    </div>
    { dropProps.isOver && <div className={'px-2 pb-3'}>
      <div className={'bg-plan-comun card'}>
        <div className='flex items-center justify-center text-center flex-col'>
          <div className='text-xs'>{course.name}</div>
          <div className='text-[0.6rem] text-gray-600'>{course.code}</div>
        </div>
        <div className='absolute bottom-2 left-2 text-[0.5rem] text-gray-600'>{course.credits} creditos</div>
      </div>
    </div>
    }
    </>
  )
}

export default CourseCard
