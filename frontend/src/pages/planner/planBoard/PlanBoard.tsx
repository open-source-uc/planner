import { useState } from 'react'
import { useAuth } from '../../../contexts/auth.context'
import SemesterColumn from './SemesterColumn'
import { FlatValidationResult } from '../../../client'
import { PseudoCourseId, PseudoCourseDetail, ValidationDigest } from '../Planner'
import 'react-toastify/dist/ReactToastify.css'

interface PlanBoardProps {
  classesGrid: PseudoCourseId[][] | null
  classesDetails: { [code: string]: PseudoCourseDetail }
  moveCourse: Function
  openModal: Function
  addCourse: Function
  remCourse: Function
  validating: Boolean
  validationResult: FlatValidationResult | null
  validationDigest: ValidationDigest
}

/**
 * The main drag-n-drop planner interface.
 * Displays several semesters, as well as several classes per semester.
 */

const PlanBoard = ({ classesGrid, classesDetails, moveCourse, openModal, addCourse, remCourse, validating, validationResult, validationDigest }: PlanBoardProps): JSX.Element => {
  const authState = useAuth()
  const [isDragging, setIsDragging] = useState(false)

  return (
    <div className= {`overflow-auto grid grid-rows-[fit-content] grid-flow-col justify-start ${validating === true ? 'pointer-events-none' : ''}`}>
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
