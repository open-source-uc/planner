import { useState, useRef } from 'react'
import SemesterColumn from './SemesterColumn'
import { type PseudoCourseId, type PseudoCourseDetail } from '../utils/Types'
import { useDndScrolling, createVerticalStrength, createHorizontalStrength } from 'react-dnd-scrolling'
import 'react-toastify/dist/ReactToastify.css'
import { type ValidationResult } from '../../../client'
import { getClassId, getValidationDigest } from '../utils/PlanBoardFunctions'

interface PlanBoardProps {
  classesGrid: PseudoCourseId[][]
  authState: any
  validationResult: ValidationResult | null
  classesDetails: Record<string, PseudoCourseDetail>
  moveCourse: Function
  openModal: Function
  addCourse: Function
  remCourse: Function
}

// Estos parametros controlan a cuantos pixeles de distancia al borde de la pantalla se activa el scroll
const vStrength = createVerticalStrength(60)
const hStrength = createHorizontalStrength(300)
/**
 * The main drag-n-drop planner interface.
 * Displays several semesters, as well as several classes per semester.
 */

const PlanBoard = ({ classesGrid = [], authState, validationResult, classesDetails, moveCourse, openModal, addCourse, remCourse }: PlanBoardProps): JSX.Element => {
  const [active, setActive] = useState<{ semester: number, index: number } | null>(null)
  const boardRef = useRef(null)
  useDndScrolling(boardRef, { horizontalStrength: hStrength, verticalStrength: vStrength })
  const validationDigest = getValidationDigest(classesGrid, validationResult)
  return (
      <div ref={boardRef} className= {'overflow-auto grid grid-rows-[fit-content] grid-flow-col justify-start'}>
        {classesGrid.map((classes: PseudoCourseId[], semester: number) => (
            <SemesterColumn
              key={semester}
              semester={semester}
              addCourse={addCourse}
              moveCourse={moveCourse}
              remCourse={remCourse}
              openModal={openModal}
              classes={classes}
              coursesId={classes.map((_, index) => getClassId(classesGrid, { semester, index }))}
              validation={validationDigest?.semesters?.[semester]}
              classesDetails={classesDetails}
              authState={authState}
              isDragging={active !== null}
              activeIndex={(active !== null && active.semester === semester) ? active.index : null}
              setActive={setActive}
            />
        ))}
        {[0, 1].map(off => (
          <SemesterColumn
            key={classesGrid.length + off}
            semester={classesGrid.length + off}
            addCourse={addCourse}
            moveCourse={moveCourse}
            remCourse={remCourse}
            openModal={openModal}
            classesDetails={classesDetails}
            authState={authState}
            coursesId={[]}
            validation={undefined}
            isDragging={active !== null}
            activeIndex={(active !== null && active.semester === classesGrid.length + off) ? active.index : null}
            setActive={setActive}
          />
        ))}
    </div>
  )
}

export default PlanBoard
