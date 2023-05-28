
import { memo, useCallback } from 'react'
import { useDrop } from 'react-dnd'
import { useAuth } from '../../../contexts/auth.context'
import { CourseDetails } from '../../../client'
import { CourseValidationDigest, PseudoCourseDetail, PseudoCourseId } from '../Planner'
import CourseCard from './CourseCard'
import deepEqual from 'fast-deep-equal'

interface SemesterColumnProps {
  classesDetails: { [code: string]: PseudoCourseDetail }
  semester: number
  addCourse: Function
  moveCourse: Function
  remCourse: Function
  openModal: Function
  classes: PseudoCourseId[]
  validationDigest: CourseValidationDigest[]
  isDragging: boolean
  setIsDragging: Function
}

const SemesterColumn = ({ classesDetails, semester, addCourse, moveCourse, remCourse, openModal, classes, validationDigest, isDragging, setIsDragging }: SemesterColumnProps): JSX.Element => {
  const authState = useAuth()
  const [dropProps, drop] = useDrop(() => ({
    accept: 'card',
    drop (course: CourseDetails & { semester: number }) {
      moveCourse(course, semester, classes.length)
    },
    collect: monitor => ({
      isOver: !!monitor.isOver()
    })
  }))
  const openSelector = useCallback((course: PseudoCourseId, semester: number, index: number) => {
    if ('equivalence' in course) openModal(course.equivalence, semester, index)
    else openModal(course, semester, index)
  }, [])
  return (
    <div className={'drop-shadow-xl w-[165px] shrink-0 bg-base-200 rounded-lg flex flex-col'}>
      <h2 className="mt-1 text-[1.2rem] text-center">{`Semestre ${semester + 1}`}</h2>
      <div className="my-2 divider"></div>
      <div>
        {
          classes.map((course: PseudoCourseId, index: number) => (
            <CourseCard
              key={index}
              semester={semester}
              index={index}
              cardData={{ ...course, semester, index, ...classesDetails[course.code] }}
              isDragging={setIsDragging}
              moveCourse={moveCourse}
              remCourse={remCourse}
              courseBlock={validationDigest[index]?.superblock ?? ''}
              openSelector={openSelector}
              hasEquivalence={course.is_concrete === false || ('equivalence' in course && course.equivalence != null)}
              hasError={validationDigest[index]?.errorIndices?.[0] != null}
              hasWarning={validationDigest[index]?.warningIndices?.[0] != null}
            />
          ))
        }
        {((authState?.passed?.length) != null) && (semester >= authState?.passed?.length) && !isDragging && <div className="h-10 mx-2 bg-slate-300 card">
        <button key="+" className="w-full" onClick={() => addCourse(semester)}>+</button>
        </div>}
      </div>
      {((authState?.passed?.length) != null) && (semester < authState?.passed?.length)
        ? null
        : <div ref={drop} className={'px-2 flex min-h-[90px] flex-grow'}>
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
