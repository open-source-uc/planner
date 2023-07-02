import { memo, type ReactNode, useRef } from 'react'
import { type DragSourceMonitor, useDrag } from 'react-dnd'
import { ReactComponent as EditWhiteIcon } from '../../../assets/editWhite.svg'
import { ReactComponent as EditBlackIcon } from '../../../assets/editBlack.svg'
import { ReactComponent as currentWhiteIcon } from '../../../assets/currentWhite.svg'
import { ReactComponent as currentBlackIcon } from '../../../assets/currentBlack.svg'
import ConditionalWrapper from '../utils/ConditionalWrapper'
import deepEqual from 'fast-deep-equal'
import { type PseudoCourseId, type PseudoCourseDetail } from '../utils/Types'

interface DraggableCardProps {
  course: PseudoCourseId
  courseDetails: PseudoCourseDetail
  courseId: { code: string, instance: number }
  isPassed: boolean
  isCurrent: boolean
  toggleDrag: Function
  remCourse: Function
  courseBlock: string
  openSelector: Function
  hasEquivalence?: boolean
  hasError: boolean
  hasWarning: boolean
}
interface CardProps {
  course: PseudoCourseId
  credits: number
  name: string
  remCourse: Function
  courseBlock: string
  openSelector: Function
  hasEquivalence?: boolean
  hasError: boolean
  hasWarning: boolean
  isPassed: boolean
  isCurrent: boolean
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

const DraggableCard = ({ course, courseDetails, courseId, isPassed, isCurrent, toggleDrag, remCourse, courseBlock, openSelector, hasEquivalence, hasError, hasWarning }: DraggableCardProps): JSX.Element => {
  const ref = useRef(null)
  const callOpenSelector = (): void => openSelector(courseId)
  const callRemCourse = (): void => remCourse(courseId)
  const [{ isDragging = false }, drag] = useDrag(() => ({
    type: 'card',
    item: () => {
      toggleDrag(true, courseId)
      return courseId
    },
    end: () => {
      toggleDrag(false, courseId)
    },
    collect (monitor) {
      return { isDragging: monitor.isDragging() }
    }
  }), [courseId])

  if (!isPassed && !isCurrent) {
    drag(ref)
  }
  return (
    <div ref={ref} draggable={true} className={`${isDragging ? 'opacity-0 z-0' : ''} mx-1 mb-3 ${(isPassed || isCurrent) ? 'cursor-not-allowed opacity-50' : 'cursor-grab'} `}>
      <ConditionalWrapper condition={course.is_concrete !== true && courseBlock != null} wrapper={(children: ReactNode) => <button className='w-full' onClick={() => { callOpenSelector() }}>{children}</button>}>
          <CourseCard
            courseBlock={courseBlock}
            course={course}
            credits={(courseDetails !== undefined && 'credits' in courseDetails) ? courseDetails.credits : ('credits' in course) ? course.credits : 0}
            name={courseDetails !== undefined ? courseDetails.name : ''}
            hasEquivalence={hasEquivalence}
            openSelector={callOpenSelector}
            remCourse={callRemCourse}
            hasWarning={hasWarning}
            hasError={hasError}
            isPassed={isPassed}
            isCurrent={isCurrent}
          />
        </ConditionalWrapper>
    </div>
  )
}

const CourseCard = memo(function _CourseCard ({ courseBlock, course, credits, name, hasEquivalence, openSelector, remCourse, hasWarning, hasError, isPassed, isCurrent }: CardProps): JSX.Element {
  const blockId = BlockInitials(courseBlock)
  const EditIcon = (blockId === 'FG') ? EditWhiteIcon : EditBlackIcon
  const CurrentIcon = (blockId === 'FG') ? currentWhiteIcon : currentBlackIcon
  // Turns out animations are a big source of lag
  const allowAnimations = false && blockId !== 'FG'

  return (
    <div className={` card group bg-block-${blockId} ${blockId === 'FG' ? 'text-white' : ''} ${course.is_concrete !== true && allowAnimations ? 'animated' : ''}`}>
      { hasEquivalence === true && (course.is_concrete === true
        ? <button onClick={() => openSelector()}><div className='opacity-60 absolute w-3 top-2 left-2'><EditIcon/></div></button>
        : <div className='opacity-60 absolute w-3 top-2 left-2'><EditIcon/></div>
      )}
      {blockId === ''
        ? <>{isPassed || isCurrent ? null : <button className='absolute top-0 right-2 hidden group-hover:inline' onClick={() => remCourse()}>x</button>}</>
        : <div className='absolute top-2 right-2 text-[0.6rem] opacity-75'>{blockId}</div>
      }
      <div className='flex items-center justify-center text-center flex-col'>
        <div className={`text-xs line-clamp-2 ${'failed' in course && course.failed !== null ? 'line-through' : ''}`}>{ name}</div>
        <div className='text-[0.6rem] opacity-75'>{course.is_concrete !== true ? 'Seleccionar Curso' : course.code}</div>
      </div>
      <div className='absolute bottom-2 left-2 text-[0.5rem] opacity-75'>{credits} créd.</div>
      { isCurrent ? <div className='opacity-60 absolute w-3 bottom-2 right-2'> <CurrentIcon/> </div> : null}

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
