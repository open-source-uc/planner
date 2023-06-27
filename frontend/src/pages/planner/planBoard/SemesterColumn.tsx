
import { memo, useCallback } from 'react'
import { useDrop } from 'react-dnd'
import { useAuth } from '../../../contexts/auth.context'
import { type CourseValidationDigest, type PseudoCourseDetail, type PseudoCourseId, type SemesterValidationDigest } from '../Planner'
import CourseCard from './CourseCard'
import deepEqual from 'fast-deep-equal'

interface SemesterColumnProps {
  classesDetails: Record<string, PseudoCourseDetail>
  semester: number
  addCourse: Function
  moveCourse: Function
  remCourse: Function
  openModal: Function
  classes: PseudoCourseId[]
  validationCourses: CourseValidationDigest[]
  validationSemester: SemesterValidationDigest | null
  isDragging: boolean
  setIsDragging: Function
}

const SemesterColumn = ({ classesDetails, semester, addCourse, moveCourse, remCourse, openModal, classes, validationCourses, validationSemester, isDragging, setIsDragging }: SemesterColumnProps): JSX.Element => {
  const authState = useAuth()
  const conditionPassed = ((authState?.student) != null) && (semester < authState.student.current_semester)
  const conditionNotPassed = ((authState?.student) != null) && (semester >= authState.student.current_semester)
  const checkInClass = ((authState?.student) != null) && (authState.student.current_semester === authState.student.next_semester - 1)
  const checkCurrent = (checkInClass && (semester === authState?.student?.current_semester))

  const [dropProps, drop] = useDrop(() => ({
    accept: 'card',
    drop (course: { name: string, code: string, index: number, semester: number, credits?: number, is_concrete?: boolean }) {
      moveCourse({ semester: course.semester, index: course.index }, { semester, index: classes.length })
    },
    collect: monitor => ({
      isOver: monitor.isOver()
    })
  }))
  const openSelector = useCallback((course: PseudoCourseId, semester: number, index: number) => {
    if ('equivalence' in course) openModal(course.equivalence, semester, index)
    else openModal(course, semester, index)
  }, [])
  let border = 'border-transparent'
  if (validationSemester != null && validationSemester.errorIndices.length > 0) border = 'border-solid border-red-300'
  else if (validationSemester != null && validationSemester.warningIndices.length > 0) border = 'border-solid border-yellow-300'
  return (
    <div className={`drop-shadow-xl w-[161px] shrink-0 bg-base-200 rounded-lg flex flex-col border-2 ${border}`}>
      {conditionPassed
        ? <><span className='line-through decoration-black/40'><h2 className="mt-1 text-[1.2rem] text-center">{`Semestre ${semester + 1}`}</h2></span><div className="my-3 divider"></div></>
        : checkCurrent ? <div className='flex flex-col text-center'><h2 className="mt-1 text-[1.2rem] text-center">{`Semestre ${semester + 1}`}</h2><p className='text-xs'>En curso</p><div className="my-1 divider"></div></div> : <><h2 className="mt-1 text-[1.2rem] text-center">{`Semestre ${semester + 1}`}</h2><div className="my-3 divider"></div></>
      }
      <div>
        {
          classes.map((course: PseudoCourseId, index: number) => (
            <CourseCard
              key={index}
              semester={semester}
              index={index}
              cardData={{ ...course, semester, index, ...classesDetails[('failed' in course ? course.failed : null) ?? course.code] }}
              isDragging={setIsDragging}
              moveCourse={moveCourse}
              remCourse={remCourse}
              courseBlock={validationCourses[index]?.superblock ?? ''}
              openSelector={() => { openSelector(course, semester, index) }}
              hasEquivalence={course.is_concrete === false || ('equivalence' in course && course.equivalence != null)}
              hasError={validationCourses[index]?.errorIndices?.[0] != null}
              hasWarning={validationCourses[index]?.warningIndices?.[0] != null}
            />
          ))
        }
        {conditionNotPassed && !checkCurrent && !isDragging && <div className="h-10 mx-2 bg-slate-300 card">
        <button key="+" className="w-full" onClick={() => addCourse(semester)}>+</button>
        </div>}
      </div>
      {conditionPassed || checkCurrent
        ? null
        : <div ref={drop} className={'px-2 flex flex-grow min-h-[90px]'}>
            {dropProps.isOver &&
              <div className={'bg-place-holder card w-full'} />
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
