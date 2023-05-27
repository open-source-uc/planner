import { useState, memo, useCallback } from 'react'
import { useDrop } from 'react-dnd'
import { CourseDetails } from '../../../client'
import { CourseValidationDigest, PseudoCourseId, PseudoCourseDetail, ValidationDigest } from '../Planner'
import CourseCard from './CourseCard'
import 'react-toastify/dist/ReactToastify.css'
import deepEqual from 'fast-deep-equal'

interface PlanBoardProps {
  classesGrid: PseudoCourseId[][] | null
  classesDetails: { [code: string]: PseudoCourseDetail }
  moveCourse: Function
  openModal: Function
  addCourse: Function
  remCourse: Function
  validationDigest: ValidationDigest
}

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

/**
    A single semester. Represents a column in the main drag-n-drop planner interface that displays a semester and its associated classes.
    Allows dropping a course into the end of the semester column.
  */
const SemesterColumn = memo(function _SemesterColumn ({ classesDetails, semester, addCourse, moveCourse, remCourse, openModal, classes, validationDigest, isDragging, setIsDragging }: SemesterColumnProps): JSX.Element {
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
        {!isDragging && <div className="h-10 mx-2 bg-slate-300 card">
        <button key="+" className="w-full" onClick={() => addCourse(semester)}>+</button>
        </div>}
      </div>
      <div ref={drop} className={'px-2 flex min-h-[90px] flex-grow'}>
        {dropProps.isOver &&
            <div className={'bg-place-holder card w-full'} />
        }
      </div>
    </div>
  )
}, checkPropEq)

/**
 * The main drag-n-drop planner interface.
 * Displays several semesters, as well as several classes per semester.
 */

const PlanBoard = ({ classesGrid, classesDetails, moveCourse, openModal, addCourse, remCourse, validationDigest }: PlanBoardProps): JSX.Element => {
  const [isDragging, setIsDragging] = useState(false)

  return (
    <div className= {'overflow-auto grid grid-rows-[fit-content] grid-flow-col justify-start'}>
      {classesGrid === null
        ? <h1>elija plan</h1>
        : <>
          {classesGrid.map((classes: PseudoCourseId[], semester: number) => (
              <SemesterColumn
                key={semester}
                semester={semester}
                addCourse={addCourse}
                moveCourse={moveCourse}
                remCourse={remCourse}
                openModal={openModal}
                classes={classes}
                classesDetails={classesDetails}
                validationDigest={validationDigest[semester]}
                isDragging={isDragging}
                setIsDragging={setIsDragging}
              />
          ))}
          {isDragging && [0, 1].map(off => (
            <SemesterColumn
              key={classesGrid.length + off}
              semester={classesGrid.length + off}
              addCourse={addCourse}
              moveCourse={moveCourse}
              remCourse={remCourse}
              openModal={openModal}
              classes={[]}
              classesDetails={classesDetails}
              validationDigest={[]}
              isDragging={isDragging}
              setIsDragging={setIsDragging}
            />
          ))}
          </>
      }
    </div>
  )
}

export default PlanBoard
