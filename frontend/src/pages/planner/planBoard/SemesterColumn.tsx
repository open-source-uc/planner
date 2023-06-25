
import { memo, useCallback, useRef } from 'react'
import { useDrop } from 'react-dnd'
import { useAuth } from '../../../contexts/auth.context'
import { type CourseValidationDigest, type PseudoCourseDetail, type PseudoCourseId, type SemesterValidationDigest } from '../utils/Types'
import DraggableCard from './CourseCard'
import deepEqual from 'fast-deep-equal'

interface SemesterColumnProps {
  classesDetails: Record<string, PseudoCourseDetail>
  semester: number
  addCourse: Function
  coursesId: Array<{ code: string, instance: number }>
  moveCourse: Function
  remCourse: Function
  openModal: Function
  classes: PseudoCourseId[]
  validationCourses: CourseValidationDigest[]
  validationSemester: SemesterValidationDigest | null
  isDragging: boolean
  setIsDragging: Function
}

const SemesterColumn = ({ classesDetails, semester, coursesId, addCourse, moveCourse, remCourse, openModal, classes, validationCourses, validationSemester, isDragging, setIsDragging }: SemesterColumnProps): JSX.Element => {
  const authState = useAuth()
  const columnRef = useRef<HTMLDivElement>(null)
  const conditionPassed = ((authState?.student) != null) && (semester < authState.student.current_semester)
  const [, drop] = useDrop(() => ({
    accept: 'card',
    drop (courseId: { code: string, instance: number }, monitor) {
      if (monitor.getClientOffset() === null || columnRef.current === null) return
      const targetIndex = Math.floor((monitor.getClientOffset().y - columnRef.current.getBoundingClientRect().top) / 100)
      moveCourse(courseId, { semester, index: targetIndex })
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

  if (!conditionPassed) {
    drop(columnRef)
  }
  return (
    <div className='drop-shadow-xl w-[161px] shrink-0 bg-base-200 rounded-lg flex flex-col'>
      {conditionPassed
        ? <span className='line-through decoration-black/40'><h2 className={`mt-1 text-[1.2rem] text-center  border-2 ${border}`}>{`Semestre ${semester + 1}`}</h2></span>
        : <h2 className={`mt-1 text-[1.2rem] text-center border-2 rounded-md ${border}`}>{`Semestre ${semester + 1}`}</h2>
      }
      <div className="my-2 divider"></div>
      <div ref={columnRef}>
        {classes.map((course: PseudoCourseId, index: number) => (
          <DraggableCard
            key={coursesId[index].code + String(coursesId[index].instance)}
            cardData={{ ...course, ...classesDetails[course.code] }}
            coursesId={coursesId[index]}
            isPassed={conditionPassed}
            isDragging={setIsDragging}
            remCourse={remCourse}
            courseBlock={validationCourses[index]?.superblock ?? ''}
            openSelector={() => { openSelector(course, semester, index) }}
            hasEquivalence={course.is_concrete === false || ('equivalence' in course && course.equivalence != null)}
            hasError={validationCourses[index]?.errorIndices?.[0] != null}
            hasWarning={validationCourses[index]?.warningIndices?.[0] != null}
          />
        ))
        }
        {!conditionPassed && !isDragging && <div className="h-10 mx-2 bg-block- card">
        <button key="+" className="w-full" onClick={() => addCourse(semester)}>+</button>
        </div>}
      </div>
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
