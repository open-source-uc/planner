import { memo, useCallback, useRef, useState, Fragment, type ReactNode, type MouseEventHandler } from 'react'
import { useDrop, type DropTargetMonitor } from 'react-dnd'
import { type PseudoCourseDetail, type PseudoCourseId, type SemesterValidationDigest } from '../utils/Types'
import DraggableCard from './CourseCard'
import deepEqual from 'fast-deep-equal'
import { type ClassId } from '../../../client'
import { type AuthState } from '../../../contexts/auth.context'
import ConditionalWrapper from '../utils/ConditionalWrapper'

function getSemesterName (admission: any[] | null, semester: number): string | null {
  if (admission == null) {
    return null
  }
  const [baseYear, baseSem] = admission
  const now = baseYear * 2 + (baseSem - 1) + semester
  const nowYear = Math.floor(now / 2)
  const nowSem = now % 2 + 1
  return `${nowYear}-${nowSem}`
}

interface SemesterColumnProps {
  classesDetails: Record<string, PseudoCourseDetail>
  authState: AuthState | null
  semester: number
  addCourse: Function
  moveCourse: Function
  remCourse: Function
  openModal: Function
  classes?: PseudoCourseId[]
  coursesId: ClassId[]
  validation: SemesterValidationDigest | undefined
  isDragging: boolean
  activeIndex: number | null
  setActive: Function
  handleContextMenu: MouseEventHandler<HTMLDivElement>
}
const SemesterColumn = ({ coursesId, validation, classesDetails, authState, semester, addCourse, moveCourse, remCourse, openModal, classes = [], isDragging, activeIndex, setActive, handleContextMenu }: SemesterColumnProps): JSX.Element => {
  const [dragged, setDragged] = useState<number | null>(null)
  const columnRef = useRef<HTMLDivElement>(null)
  const semesterIsInProgress = ((authState?.student) != null) && (authState.student.current_semester === authState.student.next_semester - 1)
  const isPassed = ((authState?.student) != null) && (semester < authState.student.current_semester)
  const isCurrent = (semesterIsInProgress && (semester === authState?.student?.current_semester))
  const semesterName = getSemesterName(authState?.student?.admission ?? null, semester)
  const totalCredits = classes.map(course => {
    const details = classesDetails[course.code]
    if ('credits' in course) {
      return course.credits
    } else if (details != null && 'credits' in details) {
      return details.credits
    } else {
      return 0
    }
  }).reduce((sum, creds) => sum + creds, 0)

  const openSelector = useCallback((course: PseudoCourseId, semester: number, index: number) => {
    if ('equivalence' in course) openModal(course.equivalence, semester, index)
    else openModal(course, semester, index)
  }, [openModal])

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
    hover () {
      setActive((prev: { semester: number, index: number }) => {
        if (prev.index !== -1 || prev.semester !== semester) return { semester, index: -1 }
        return prev
      })
    }
  }))

  let border = 'border-transparent'
  if ((validation?.errors?.length ?? 0) > 0) border = 'border-solid border-red-300'
  else if ((validation?.warnings?.length ?? 0) > 0) border = 'border-solid border-yellow-300'

  if (!isPassed && !isCurrent) {
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

  const toggleDrag = useCallback((isStart: boolean, courseId: ClassId) => {
    const index = coursesId.indexOf(courseId)
    if (isStart) {
      setDragged(index)
      setActive({ semester, index })
    } else {
      setDragged(null)
      setActive(null)
    }
  }, [coursesId, semester, setActive])

  const openSelectorSemester = useCallback((courseId: ClassId) => {
    const index = coursesId.indexOf(courseId)
    openSelector(classes[index], semester, index)
  }, [coursesId, openSelector, classes, semester])

  return (
    <div className={'drop-shadow-xl w-[161px] shrink-0 bg-base-200 rounded-lg flex flex-col'}>
      <div className={`border-2 ${border} rounded-lg`}>
      <div className='flex flex-col text-center'>
        <ConditionalWrapper condition={isPassed} wrapper={(children: ReactNode) => <span className='line-through decoration-black/40'>{children}</span>}>
          <h2 className="mt-1 text-[1.2rem] text-center">{`Semestre ${semester + 1}`}</h2>
        </ConditionalWrapper>
        <>
          <p className="text-[0.6rem] opacity-75">{semesterName != null && `${semesterName} | `}{totalCredits} créd.{isCurrent ? ' (en curso)' : ''}</p>
          <div className="my-1 divider"></div>
        </>
      </div>
      <div ref={columnRef}>
        {classes.map((course: PseudoCourseId, index: number) => {
          const classId = coursesId[index]
          const courseValidation = validation?.courses?.[index]
          const equivDetails = 'equivalence' in course && course.equivalence != null ? classesDetails[course.equivalence.code] : null
          const equivCourses = equivDetails != null && 'courses' in equivDetails ? equivDetails.courses : null
          const showEquivalence = !isPassed && !isCurrent && (course.is_concrete === false || (equivCourses?.length ?? 0) > 1)
          return (
            <Fragment key={index}>
              {(activeIndexHandler(index)) && <div key="placeholder" className="card mx-1 mb-3 bg-place-holder"/>}
              <div className={`${dragged === index ? 'dragged' : ''}`}>
                <DraggableCard
                  key={course.code + String(classId.instance)}
                  course={course}
                  courseDetails={classesDetails[('failed' in course ? course.failed : null) ?? course.code] }
                  courseId={classId}
                  isPassed={isPassed}
                  isCurrent={isCurrent}
                  toggleDrag={toggleDrag}
                  remCourse={remCourse}
                  courseBlock={courseValidation?.superblock ?? ''}
                  openSelector={openSelectorSemester}
                  showEquivalence={showEquivalence}
                  hasError={(courseValidation?.errors?.length ?? 0) > 0}
                  hasWarning={(courseValidation?.warnings?.length ?? 0) > 0}
                  handleContextMenu={handleContextMenu}
                />
              </div>
            </Fragment>
          )
        })}
      </div>
      </div>
      {(isPassed || isCurrent)
        ? null
        : <div ref={dropEnd} className={'w-full px-1 flex flex-grow min-h-[90px]'}>
            {!isDragging && <div className="w-full h-10 bg-block- card">
              <button key="+" className="w-full" onClick={() => addCourse(semester)}>+</button>
            </div>}
            {(activeIndex === -1 || activeIndexHandler(classes.length)) &&
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
