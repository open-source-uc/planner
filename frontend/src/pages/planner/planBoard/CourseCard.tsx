import { useRef } from 'react'
import { useDrag, useDrop } from 'react-dnd'
import { Course, Equivalence, ConcreteId, EquivalenceId } from '../../../client'
import editWhiteIcon from '../../../assets/editWhite.svg'
import editBlackIcon from '../../../assets/editBlack.svg'

interface CourseCardProps {
  course: ((Course & ConcreteId) | (Equivalence & EquivalenceId)) & { semester: number }
  isDragging: Function
  handleMove: Function
  remCourse: Function
  courseBlock: string | null
  openSelector: Function
}

const CourseCard = ({ course, isDragging, handleMove, remCourse, courseBlock, openSelector }: CourseCardProps): JSX.Element => {
  const ref = useRef(null)
  const [collected = { isDragging: false }, drag] = useDrag(() => ({
    type: 'card',
    item: () => {
      isDragging(true)
      return course
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

  const BlockInitials = (courseBlock: string): string => {
    switch (courseBlock) {
      case 'CienciasBasicas':
        return 'PC'
      case 'BaseGeneral':
        return 'PC'
      case 'FormacionGeneral':
        return 'FG'
      case 'Major':
        return 'M'
      case 'Minor':
        return 'm'
    }
    return ''
  }

  drag(drop(ref))
  return (
    <>
    <div ref={ref} draggable={true} className={`px-2 ${!collected.isDragging ? 'pb-3 cursor-grab' : 'cursor-grabbing'} `}>
      {dropProps.isOver
        ? <div className={'card bg-place-holder'} />
        : <>{!collected.isDragging && <div className={`card group ${courseBlock != null ? courseBlock : ''}`}>
          { (course.is_concrete === false) && (courseBlock === 'FormacionGeneral'
            ? <button onClick={() => openSelector()}><img className='absolute w-3 top-2 left-2' src={editWhiteIcon} alt="Seleccionar Curso" /></button>
            : <button onClick={() => openSelector()}><img className='absolute w-3 top-2 left-2' src={editBlackIcon} alt="Seleccionar Curso" /></button>)
          }
          {courseBlock == null
            ? <button className='absolute top-0 right-2 hidden group-hover:inline' onClick={() => remCourse()}>x</button>
            : <div className='absolute top-2 right-2 text-[0.6rem] opacity-75'>{BlockInitials(courseBlock)}</div>}
          <div className='flex items-center justify-center text-center flex-col'>
            <div className='text-xs'>{ course.name}</div>
            <div className='text-[0.6rem] opacity-75'>{course.code}</div>
          </div>
          <div className='absolute bottom-2 left-2 text-[0.5rem] opacity-75'>{course.credits} creditos</div>
      </div>}
      </>}
    </div>
    { dropProps.isOver && <div className={'px-2 pb-3'}>
      <div className={`${courseBlock != null ? courseBlock : ''}  card`}>
        {courseBlock != null && <div className='absolute top-2 right-2 text-[0.6rem] opacity-75'>{BlockInitials(courseBlock)}</div>}
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
