import { useRef } from 'react'
import { useDrag, useDrop } from 'react-dnd'
import { Course } from '../../../client'
import { PseudoCourse } from './PlanBoard'

interface CourseCardProps {
  course: Course & { semester: number } & PseudoCourse
  isDragging: Function
  handleMove: Function
  remCourse: Function
  courseBlock: string | null
}

const CourseCard = ({ course, isDragging, handleMove, remCourse, courseBlock }: CourseCardProps): JSX.Element => {
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
        ? <div className={'card'} />
        : <>{!collected.isDragging && <div className={`card group ${courseBlock != null ? courseBlock : ''}`}>
          {courseBlock == null && <button className='absolute top-0 right-2 hidden group-hover:inline' onClick={() => remCourse()}>x</button>}
          <div className='flex items-center justify-center text-center flex-col'>
            <div className='text-xs'>{ course.is_concrete === true ? course.name : 'Seleccionar Curso!' }</div>
            <div className='text-[0.6rem] opacity-75'>{course.code}</div>
          </div>
          <div className='absolute bottom-2 left-2 text-[0.5rem] opacity-75'>{course.credits} creditos</div>
      </div>}
      </>}
    </div>
    { dropProps.isOver && <div className={'px-2 pb-3'}>
      <div className={`${courseBlock != null ? courseBlock : ''}  card`}>
        <div className='flex items-center justify-center text-center flex-col'>
          <div className='text-xs'>{ course.is_concrete === true ? course.name : 'Seleccionar Curso!'}</div>
          <div className='text-[0.6rem] opacity-75'>{ course.code}</div>
        </div>
        <div className='absolute bottom-2 left-2 text-[0.5rem] opacity-75'>{course.credits} creditos</div>
      </div>
    </div>
    }
    </>
  )
}

export default CourseCard
