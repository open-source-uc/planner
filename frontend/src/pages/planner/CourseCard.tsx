import { useRef } from 'react'
import { useDrag, useDrop } from 'react-dnd'

const CourseCard = ({ course, isDragging, handleMove, remCourse }: { course: { credits: number, name?: string, code: string, semester: number }, isDragging: Function, handleMove: Function, remCourse: Function }): JSX.Element => {
  const ref = useRef(null)
  const [collected = { isDragging: false }, drag] = useDrag(
    () => ({
      type: 'card',

      item: () => {
        isDragging(true)
        return { course }
      },
      // i want to freeze the card position when the drag is droped, like this:
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
    drop (course: { code: string, semester: number }) {
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
          <div className='flex items-center justify-center text-center flex-col'>
            <div className='text-xs'>{course.name !== undefined ? course.name : '???'}</div>
            <div className='text-[0.6rem] text-gray-600'>{course.code}</div>
          </div>
          <div className='absolute bottom-2 left-2 text-[0.5rem] text-gray-600'>{course.credits !== undefined ? course.credits : '??'} creditos</div>
      </div>}
      </>}
    </div>
    {
      dropProps.isOver && <div className={'px-2 pb-3'}>
      <div className={'bg-plan-comun card relative group flex justify-center'}>
          <div className='flex items-center justify-center text-center flex-col'>
            <div className='text-xs'>{course.name !== undefined ? course.name : '???'}</div>
            <div className='text-[0.6rem] text-gray-600'>{course.code}</div>
          </div>
        <div className='absolute bottom-2 left-2 text-[0.5rem] text-gray-600'>{course.credits !== undefined ? course.credits : '??'} creditos</div>
      </div>
    </div>
    }
    </>
  )
}

export default CourseCard
