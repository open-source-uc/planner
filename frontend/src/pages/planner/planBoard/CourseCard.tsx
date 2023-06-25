import { memo, type ReactNode, useRef } from 'react'
import { useDrag } from 'react-dnd'
import { ReactComponent as EditWhiteIcon } from '../../../assets/editWhite.svg'
import { ReactComponent as EditBlackIcon } from '../../../assets/editBlack.svg'
import ConditionalWrapper from '../utils/ConditionalWrapper'
import deepEqual from 'fast-deep-equal'

interface DraggableCardProps {
  cardData: { name: string, code: string, credits?: number, is_concrete?: boolean }
  coursesId: { code: string, instance: number }
  isPassed: boolean
  isDragging: Function
  remCourse: Function
  courseBlock: string
  openSelector: Function
  hasEquivalence?: boolean
  hasError: boolean
  hasWarning: boolean
}
interface CardProps {
  cardData: { name: string, code: string, credits?: number, is_concrete?: boolean }
  remCourse: Function
  courseBlock: string
  openSelector: Function
  hasEquivalence?: boolean
  hasError: boolean
  hasWarning: boolean
  isPassed: boolean
}

const BlockInitials = (courseBlock: string): string => {
  switch (courseBlock) {
    case 'Ciencias':
      return 'PC'
    case 'Base':
      return 'PC'
    case 'Formacion':
      return 'FG'
    case 'Major':
      return 'M'
    case 'Minor':
      return 'm'
    case 'Ingeniero':
      return 'T'
  }
  return ''
}

const DraggableCard = ({ cardData, coursesId, isPassed, isDragging, remCourse, courseBlock, openSelector, hasEquivalence, hasError, hasWarning }: DraggableCardProps): JSX.Element => {
  const ref = useRef(null)

  const [collected = { isDragging: false }, drag] = useDrag(() => ({
    type: 'card',
    item: () => {
      isDragging(true)
      return coursesId
    },
    end () {
      isDragging(false)
    },
    collect (monitor) {
      return { isDragging: monitor.isDragging() }
    }
  }))

  if (!isPassed) {
    drag(ref)
  }

  return (
    <div ref={ref} draggable={true} className={`px-2 ${!collected.isDragging ? 'pb-3' : ''} ${isPassed ? 'cursor-not-allowed opacity-50' : 'cursor-grab'} `}>
      {!collected.isDragging &&
        <ConditionalWrapper condition={cardData.is_concrete !== true && courseBlock != null} wrapper={(children: ReactNode) => <button className='w-full' onClick={() => openSelector()}>{children}</button>}>
            <CourseCard
              courseBlock={courseBlock}
              cardData={cardData}
              hasEquivalence={hasEquivalence}
              openSelector={openSelector}
              remCourse={remCourse}
              hasWarning={hasWarning}
              hasError={hasError}
              isPassed={isPassed}
            />
          </ConditionalWrapper>
        }
    </div>
  )
}

const CourseCard = memo(function _CourseCard ({ courseBlock, cardData, hasEquivalence, openSelector, remCourse, hasWarning, hasError, isPassed }: CardProps): JSX.Element {
  const blockId = BlockInitials(courseBlock)
  const EditIcon = (blockId === 'FG') ? EditWhiteIcon : EditBlackIcon

  // Turns out animations are a big source of lag
  const allowAnimations = false && blockId !== 'FG'

  return (
    <div className={`card group bg-block-${blockId} ${blockId === 'FG' ? 'text-white' : ''} ${cardData.is_concrete !== true && allowAnimations ? 'animated' : ''}`}>
      { hasEquivalence === true && (cardData.is_concrete === true
        ? <button onClick={() => openSelector()}><div className='opacity-60 absolute w-3 top-2 left-2'><EditIcon/></div></button>
        : <div className='opacity-60 absolute w-3 top-2 left-2'><EditIcon/></div>
      )}
      {blockId === ''
        ? !isPassed && <button className='absolute top-0 right-2 hidden group-hover:inline' onClick={() => remCourse()}>x</button>
        : <div className='absolute top-2 right-2 text-[0.6rem] opacity-75'>{blockId}</div>
      }
      <div className='flex items-center justify-center text-center flex-col'>
        <div className='text-xs line-clamp-2'>{cardData.name}</div>
        <div className='text-[0.6rem] opacity-75'>{cardData.is_concrete !== true ? 'Seleccionar Curso' : cardData.code}</div>
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
})

export default memo(DraggableCard, deepEqual)
