import { memo, useCallback, useRef, useState, Fragment } from 'react'
import { useDrop, type DropTargetMonitor } from 'react-dnd'
import { useAuth } from '../../../contexts/auth.context'
import { type CourseValidationDigest, type PseudoCourseDetail, type CourseId, type PseudoCourseId, type SemesterValidationDigest } from '../utils/Types'
import DraggableCard from './CourseCard'
import deepEqual from 'fast-deep-equal'

interface SemesterColumnProps {
  classesDetails: Record<string, PseudoCourseDetail>
  semester: number
  addCourse: Function
  coursesId?: Array<{ code: string, instance: number }>
  moveCourse: Function
  remCourse: Function
  openModal: Function
  classes?: PseudoCourseId[]
  validationCourses?: CourseValidationDigest[]
  validationSemester: SemesterValidationDigest | null
  isDragging: boolean
  activeIndex: number | null
  setActive: Function
}
const SemesterColumn = ({ classesDetails, semester, coursesId = [], addCourse, moveCourse, remCourse, openModal, classes = [], validationCourses = [], validationSemester, isDragging, activeIndex, setActive }: SemesterColumnProps): JSX.Element => {
  const [dragged, setDragged] = useState<number | null>(null)
  const authState = useAuth()
  const columnRef = useRef<HTMLDivElement>(null)
  const conditionPassed = ((authState?.student) != null) && (semester < authState.student.current_semester)
  const conditionNotPassed = ((authState?.student) != null) && (semester >= authState.student.current_semester)
  const checkInClass = ((authState?.student) != null) && (authState.student.current_semester === authState.student.next_semester - 1)
  const checkCurrent = (checkInClass && (semester === authState?.student?.current_semester))

  const openSelector = useCallback((course: PseudoCourseId, semester: number, index: number) => {
    if ('equivalence' in course) openModal(course.equivalence, semester, index)
    else openModal(course, semester, index)
  }, [])

  const [, drop] = useDrop(() => ({
    accept: 'card',
    drop (courseId: { code: string, instance: number }, monitor) {
      const clientOffset = monitor.getClientOffset()
      if (clientOffset === null || columnRef.current === null) return
      const targetIndex = Math.floor((clientOffset.y - columnRef.current.getBoundingClientRect().top) / 100)
      setActive(null)
      moveCourse(courseId, { semester, index: targetIndex })
    },
    hover (item, monitor: DropTargetMonitor) {
      const clientOffset = monitor.getClientOffset()
      if (clientOffset === null || columnRef.current === null) return
      const targetIndex = Math.floor((clientOffset.y - columnRef.current.getBoundingClientRect().top) / 100)
      // No se si era por ser un objeto o por algo del react-dnd pero a veces se actualizaba demas el activeIndex
      setActive((prev: { semester: number, index: number }) => {
        if (prev.index !== targetIndex || prev.semester !== semester) return { semester, index: targetIndex }
        return prev
      })
    }
  }), [])

  const [, dropEnd] = useDrop(() => ({
    accept: 'card',
    drop (courseId: { code: string, instance: number }) {
      setActive(null)
      moveCourse(courseId, { semester, index: -1 })
    },
    hover (item, monitor: DropTargetMonitor) {
      setActive((prev: { semester: number, index: number }) => {
        if (prev.index !== -1 || prev.semester !== semester) return { semester, index: -1 }
        return prev
      })
    }
  }))

  let border = 'border-transparent'
  if (validationSemester != null && validationSemester.errorIndices.length > 0) border = 'border-solid border-red-300'
  else if (validationSemester != null && validationSemester.warningIndices.length > 0) border = 'border-solid border-yellow-300'

  if (!conditionPassed && !checkCurrent) {
    drop(columnRef)
  }
  const activeIndexHandler = useCallback(
    (index: number): boolean => {
      if (activeIndex === null) return false
      if (dragged === null) {
        if (activeIndex === index) return true
      } else {
        if (activeIndex === index && dragged > index) return true
        if (activeIndex === index - 1 && dragged < index) return true
      }
      return false
    },
    [activeIndex, dragged]
  )

  const toggleDrag = useCallback((isStart: boolean, courseId: CourseId) => {
    const index = coursesId.indexOf(courseId)
    if (isStart) {
      setDragged(index)
      setActive({ semester, index })
    } else {
      setDragged(null)
      setActive(null)
    }
  }, [coursesId])

  const openSelectorSemester = useCallback((courseId: CourseId) => {
    const index = coursesId.indexOf(courseId)
    openSelector(classes[index], semester, index)
  }, [coursesId, classes])

  return (
    <div className={`drop-shadow-xl w-[161px] shrink-0 bg-base-200 rounded-lg flex flex-col border-2 ${border} `}>
      {conditionPassed
        ? <><span className='line-through decoration-black/40'><h2 className="mt-1 text-[1.2rem] text-center">{`Semestre ${semester + 1}`}</h2></span><div className="my-3 divider"></div></>
        : checkCurrent
          ? <div className='flex flex-col text-center'><h2 className="mt-1 text-[1.2rem] text-center">{`Semestre ${semester + 1}`}</h2><p className='text-xs'>En curso</p><div className="my-1 divider"></div></div>
          : <><h2 className="mt-1 text-[1.2rem] text-center">{`Semestre ${semester + 1}`}</h2><div className="my-3 divider"></div></>
      }
      <div ref={columnRef}>
        {classes.map((course: PseudoCourseId, index: number) => {
          return (
            <Fragment key={index}>
              {(activeIndexHandler(index)) && <div key="placeholder" className="card mx-2 mb-3 bg-place-holder"/>}
              <div className={`${dragged === index ? 'opacity-0 absolute w-full' : ''}`}>
                <DraggableCard
                  key={coursesId[index].code + String(coursesId[index].instance)}
                  course={course}
                  courseDetails={classesDetails[course.code]}
                  courseId={coursesId[index]}
                  isPassed={conditionPassed}
                  isCurrent={checkCurrent}
                  toggleDrag={toggleDrag}
                  remCourse={remCourse}
                  courseBlock={validationCourses[index]?.superblock ?? ''}
                  openSelector={openSelectorSemester}
                  hasEquivalence={course.is_concrete === false || ('equivalence' in course && course.equivalence != null)}
                  hasError={validationCourses[index]?.errorIndices?.[0] != null}
                  hasWarning={validationCourses[index]?.warningIndices?.[0] != null}
                />
              </div>
            </Fragment>
          )
        })}
        {conditionNotPassed && !checkCurrent && !isDragging && <div className="h-10 mx-1 bg-block- card">
        <button key="+" className="w-full" onClick={() => addCourse(semester)}>+</button>
        </div>}
      </div>
      {conditionPassed || checkCurrent
        ? null
        : <div ref={dropEnd} className={'w-full px-2 flex flex-grow min-h-[90px]'}>
            {activeIndex === -1 &&
              <div key="placeholder" className="w-full card bg-place-holder" />
            }
          </div>
      }
    </div>
  )
}
function checkPropEq (prev: any, next: any): boolean {
  for (const key of Object.keys(next)) {
    const nxt = next[key]
    const prv = prev[key]
    if (nxt !== prv) {
      if (key === 'validationDigest') {
        // Deep comparison
        if (!deepEqual(nxt, prv)) return false
      } else {
        // Shallow comparison
        return false
      }
    }
  }
  return true
}

export default memo(SemesterColumn, checkPropEq)
