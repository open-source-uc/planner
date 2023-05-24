import { memo, useRef } from 'react'
import { useDrag, useDrop } from 'react-dnd'
import { PseudoCourseDetail } from '../Planner'
import editWhiteIcon from '../../../assets/editWhite.svg'
import editBlackIcon from '../../../assets/editBlack.svg'
import deepEqual from 'fast-deep-equal'

interface CourseCardProps {
  semester: number
  index: number
  cardData: { name: string, code: string, index: number, semester: number, credits?: number, is_concrete?: boolean }
  isDragging: Function
  moveCourse: Function
  remCourse: Function
  courseBlock: string
  openSelector: Function
  hasEquivalence?: boolean
  hasError: boolean
  hasWarning: boolean
}
interface CardProps {
  semester: number
  index: number
  cardData: { name: string, code: string, index: number, semester: number, credits?: number, is_concrete?: boolean }
  remCourse: Function
  courseBlock: string
  openSelector: Function
  hasEquivalence?: boolean
  hasError: boolean
  hasWarning: boolean
}

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

const CourseCard = ({ semester, index, cardData, isDragging, moveCourse, remCourse, courseBlock, openSelector, hasEquivalence, hasError, hasWarning }: CourseCardProps): JSX.Element => {
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
    drop (course: PseudoCourseDetail) {
      moveCourse(course, semester, index)
      return course
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
      <div ref={ref} draggable={true} className={`px-2 ${!collected.isDragging ? 'pb-3 cursor-grab' : 'cursor-grabbing'} `}>
      {!collected.isDragging && <>{dropProps.isOver
        ? <div className={'card bg-place-holder'} />
        : <div> {!collected.isDragging && ((cardData.is_concrete !== true && courseBlock != null)
          ? <button className='w-full' onClick={() => openSelector(cardData, semester, index)}>
              <Card
                semester={semester}
                index={index}
                courseBlock={courseBlock}
                cardData={cardData}
                hasEquivalence={hasEquivalence}
                openSelector={openSelector}
                remCourse={remCourse}
                hasWarning={hasWarning}
                hasError={hasError}
              />
            </button>
          : <Card
            semester={semester}
            index={index}
                courseBlock={courseBlock}
                cardData={cardData}
                hasEquivalence={hasEquivalence}
                openSelector={openSelector}
                remCourse={remCourse}
                hasWarning={hasWarning}
                hasError={hasError}
              />)}
          </div>}
          </>}
      </div>
      {!collected.isDragging && dropProps.isOver && <div className={'px-2 pb-3'}>
      <Card
        semester={semester}
        index={index}
        courseBlock={courseBlock}
        cardData={cardData}
        hasEquivalence={hasEquivalence}
        openSelector={openSelector}
        remCourse={remCourse}
        hasWarning={hasWarning}
        hasError={hasError}
      />
      </div>
      }
    </>
  )
}

const Card = ({ semester, index, courseBlock, cardData, hasEquivalence, openSelector, remCourse, hasWarning, hasError }: CardProps): JSX.Element => {
  // Turns out animations are a big source of lag
  const allowAnimations = true

  return (
    <div className={`card group ${courseBlock} ${cardData.is_concrete !== true && allowAnimations ? 'animated' : ''}`}>
      { hasEquivalence === true && (courseBlock === 'FormacionGeneral'
        ? cardData.is_concrete === true
          ? <button onClick={() => openSelector(cardData, semester, index)}><img className='opacity-60 absolute w-3 top-2 left-2' src={editWhiteIcon} alt="Seleccionar Curso" /></button>
          : <img className='opacity-60 absolute w-3 top-2 left-2' src={editWhiteIcon} alt="Seleccionar Curso" />
        : cardData.is_concrete === true
          ? <button onClick={() => openSelector(cardData, semester, index)}><img className='opacity-60 absolute w-3 top-2 left-2' src={editBlackIcon} alt="Seleccionar Curso" /></button>
          : <img className='opacity-60 absolute w-3 top-2 left-2' src={editBlackIcon} alt="Seleccionar Curso" />)
      }
      {courseBlock === ''
        ? <button className='absolute top-0 right-2 hidden group-hover:inline' onClick={() => remCourse(semester, index)}>x</button>
        : <div className='absolute top-2 right-2 text-[0.6rem] opacity-75'>{BlockInitials(courseBlock)}</div>}
      <div className='flex items-center justify-center text-center flex-col'>
        <div className='text-xs line-clamp-2'>{cardData.name}</div>
        <div className='text-[0.6rem] opacity-75'>{cardData.is_concrete !== true ? `Seleccionar Curso  (${cardData.code})` : cardData.code}</div>
      </div>
      <div className='absolute bottom-2 left-2 text-[0.5rem] opacity-75'>{cardData.credits} créd.</div>
      {hasError && <span className="flex absolute h-3 w-3 top-0 right-0 -mt-1 -mr-1">
        <span className={`${allowAnimations ? 'animate-ping' : ''} absolute inline-flex h-full w-full rounded-full bg-red-300 opacity-90`}></span>
        <span className="relative inline-flex rounded-full h-3 w-3 bg-red-400"></span>
      </span> }
      {!hasError && hasWarning && <span className="flex absolute h-3 w-3 top-0 right-0 -mt-1 -mr-1">
        <span className={`${allowAnimations ? 'animate-ping' : ''} absolute inline-flex h-full w-full rounded-full bg-yellow-300 opacity-90`}></span>
        <span className="relative inline-flex rounded-full h-3 w-3 bg-yellow-400"></span>
      </span> }
  </div>
  )
}

export default memo(CourseCard, deepEqual)
