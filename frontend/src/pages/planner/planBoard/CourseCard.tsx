import { useRef } from 'react'
import { useDrag, useDrop } from 'react-dnd'
import { Course } from '../../../client'
import editWhiteIcon from '../../../assets/editWhite.svg'
import editBlackIcon from '../../../assets/editBlack.svg'

interface CourseCardProps {
  cardData: { name: string, code: string, credits?: number, semester: number, is_concrete?: boolean }
  isDragging: Function
  handleMove: Function
  remCourse: Function
  courseBlock: string | null
  openSelector: Function
  hasEquivalence?: boolean
}

const CourseCard = ({ cardData, isDragging, handleMove, remCourse, courseBlock, openSelector, hasEquivalence }: CourseCardProps): JSX.Element => {
  const ref = useRef(null)
  const [collected = { isDragging: false }, drag] = useDrag(() => ({
    type: 'card',
    item: () => {
      isDragging(true)
      return cardData
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

  const Card = (): JSX.Element => {
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
    return (
      <div className={`card group ${courseBlock != null ? courseBlock : ''} ${cardData.is_concrete !== true ? 'animated' : ''}`}>
        { hasEquivalence === true && (courseBlock === 'FormacionGeneral'
          ? cardData.is_concrete === true
            ? <button onClick={() => openSelector()}><img className='opacity-60 absolute w-3 top-2 left-2' src={editWhiteIcon} alt="Seleccionar Curso" /></button>
            : <><img className='opacity-60 absolute w-3 top-2 left-2' src={editWhiteIcon} alt="Seleccionar Curso" />
            <span className="flex absolute h-3 w-3 top-0 right-0 -mt-1 -mr-1">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-300 opacity-90"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-red-400"></span>
            </span></>
          : cardData.is_concrete === true
            ? <button onClick={() => openSelector()}><img className='opacity-60 absolute w-3 top-2 left-2' src={editBlackIcon} alt="Seleccionar Curso" /></button>
            : <><img className='opacity-60 absolute w-3 top-2 left-2' src={editBlackIcon} alt="Seleccionar Curso" /><span className="flex absolute h-3 w-3 top-0 right-0 -mt-1 -mr-1">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-300 opacity-90"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-400"></span>
          </span></>)
        }
        {courseBlock == null
          ? <button className='absolute top-0 right-2 hidden group-hover:inline' onClick={() => remCourse()}>x</button>
          : <div className='absolute top-2 right-2 text-[0.6rem] opacity-75'>{BlockInitials(courseBlock)}</div>}
        <div className='flex items-center justify-center text-center flex-col'>
          <div className='text-xs'>{cardData.name}</div>
          <div className='text-[0.6rem] opacity-75'>{cardData.code}</div>
        </div>
        <div className='absolute bottom-2 left-2 text-[0.5rem] opacity-75'>{cardData.credits} créd.</div>
    </div>
    )
  }

  drag(drop(ref))
  return (
    <>
      <div ref={ref} draggable={true} className={`px-2 ${!collected.isDragging ? 'pb-3 cursor-grab' : 'cursor-grabbing'} `}>
      {!collected.isDragging && <>{dropProps.isOver
        ? <div className={'card bg-place-holder'} />
        : <> {!collected.isDragging && (cardData.is_concrete !== true
          ? <button className='w-full' onClick={() => openSelector()}> <Card /></button>
          : <Card />)}</>}
          </>}
      </div>
      {!collected.isDragging && dropProps.isOver && <div className={'px-2 pb-3'}>
        <Card />
      </div>
      }
    </>
  )
}

export default CourseCard
