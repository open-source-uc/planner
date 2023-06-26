import { useState, useRef } from 'react'
import SemesterColumn from './SemesterColumn'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import { type PseudoCourseId, type PseudoCourseDetail, type ValidationDigest, type PlanDigest } from '../utils/Types'
import { useDndScrolling, createVerticalStrength, createHorizontalStrength } from 'react-dnd-scrolling'
import 'react-toastify/dist/ReactToastify.css'

interface PlanBoardProps {
  classesGrid: PseudoCourseId[][]
  planDigest: PlanDigest
  classesDetails: Record<string, PseudoCourseDetail>
  moveCourse: Function
  openModal: Function
  addCourse: Function
  remCourse: Function
  validationDigest: ValidationDigest
}

// Estos parametros controlan a cuantos pixeles de distancia al borde de la pantalla se activa el scroll
const vStrength = createVerticalStrength(60)
const hStrength = createHorizontalStrength(250)
/**
 * The main drag-n-drop planner interface.
 * Displays several semesters, as well as several classes per semester.
 */

const PlanBoard = ({ classesGrid = [], planDigest, classesDetails, moveCourse, openModal, addCourse, remCourse, validationDigest }: PlanBoardProps): JSX.Element => {
  const [active, setActive] = useState(null)
  const boardRef = useRef(null)
  useDndScrolling(boardRef, { horizontalStrength: hStrength, verticalStrength: vStrength })

  return (
    <DndProvider backend={HTML5Backend}>
      <div ref={boardRef} className= {'overflow-auto grid grid-rows-[fit-content] grid-flow-col justify-start gap-1'}>
        {classesGrid.map((classes: PseudoCourseId[], semester: number) => (
            <SemesterColumn
              key={semester}
              semester={semester}
              coursesId={planDigest.indexToId[semester]}
              addCourse={addCourse}
              moveCourse={(dragId: { code: string, instance: number }, dropIndex: { semester: number, index: number }) => moveCourse({ semester: planDigest.idToIndex[dragId.code][dragId.instance][0], index: planDigest.idToIndex[dragId.code][dragId.instance][1] }, dropIndex)}
              remCourse={remCourse}
              openModal={openModal}
              classes={classes}
              classesDetails={classesDetails}
              validationCourses={validationDigest.courses[semester]}
              validationSemester={validationDigest.semesters[semester]}
              isDragging={active !== null}
              activeIndex={(active !== null && active.semester === semester) ? active.index : null}
              setActive={setActive}
            />
        ))}
        {active !== null && [0, 1].map(off => (
          <SemesterColumn
            key={classesGrid.length + off}
            semester={classesGrid.length + off}
            coursesId={[]}
            addCourse={addCourse}
            moveCourse={moveCourse}
            remCourse={remCourse}
            openModal={openModal}
            classes={[]}
            classesDetails={classesDetails}
            validationCourses={[]}
            validationSemester={null}
            isDragging={active !== null}
            activeIndex={(active !== null && active.semester === classesGrid.length + off) ? 0 : null}
            setActive={setActive}
          />
        ))}
    </div>
    </DndProvider>
  )
}

export default PlanBoard
