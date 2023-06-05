import { useState } from 'react'
import SemesterColumn from './SemesterColumn'
import { PseudoCourseId, PseudoCourseDetail, ValidationDigest } from '../Planner'
import 'react-toastify/dist/ReactToastify.css'

interface PlanBoardProps {
  classesGrid: PseudoCourseId[][] | null
  classesDetails: { [code: string]: PseudoCourseDetail }
  moveCourse: Function
  openModal: Function
  addCourse: Function
  remCourse: Function
  validationDigest: ValidationDigest
}

/**
 * The main drag-n-drop planner interface.
 * Displays several semesters, as well as several classes per semester.
 */

const PlanBoard = ({ classesGrid, classesDetails, moveCourse, openModal, addCourse, remCourse, validationDigest }: PlanBoardProps): JSX.Element => {
  const [isDragging, setIsDragging] = useState(false)

  return (
    <div className= {'overflow-auto grid grid-rows-[fit-content] grid-flow-col justify-start gap-1'}>
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
                validationCourses={validationDigest.courses[semester]}
                validationSemester={validationDigest.semesters[semester]}
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
              validationCourses={[]}
              validationSemester={null}
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
