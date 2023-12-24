import { useState, useRef } from 'react'
import SemesterColumn from './SemesterColumn'
import { type PseudoCourseId, type PseudoCourseDetail, type ValidationDigest, type PlanDigest } from '../utils/Types'
import { useDndScrolling, createVerticalStrength, createHorizontalStrength } from 'react-dnd-scrolling'
import 'react-toastify/dist/ReactToastify.css'

import { usePDF } from 'react-to-pdf'

interface PlanBoardProps {
  classesGrid: PseudoCourseId[][]
  authState: any
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
const hStrength = createHorizontalStrength(300)
/**
 * The main drag-n-drop planner interface.
 * Displays several semesters, as well as several classes per semester.
 */

const PlanBoard = ({ classesGrid = [], authState, planDigest, classesDetails, moveCourse, openModal, addCourse, remCourse, validationDigest }: PlanBoardProps): JSX.Element => {
  const [active, setActive] = useState<{ semester: number, index: number } | null>(null)
  const boardRef = useRef(null)
  useDndScrolling(boardRef, { horizontalStrength: hStrength, verticalStrength: vStrength })

  const { toPDF, targetRef } = usePDF({
    filename: 'malla.pdf',
    page: {
      orientation: 'landscape'
    }
  })

  return (
    <div>
      <button onClick={() => { toPDF() }}>Download PDF</button>
      <div ref={boardRef} className= {'overflow-auto grid'}>
        <div ref={targetRef} className='grid  grid-rows-[fit-content] grid-flow-col justify-start'>
          {classesGrid.map((classes: PseudoCourseId[], semester: number) => (
              <SemesterColumn
                key={semester}
                semester={semester}
                coursesId={planDigest.indexToId[semester]}
                addCourse={addCourse}
                moveCourse={moveCourse}
                remCourse={remCourse}
                openModal={openModal}
                classes={classes}
                classesDetails={classesDetails}
                authState={authState}
                validationCourses={validationDigest.courses[semester]}
                validationSemester={validationDigest.semesters[semester]}
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
              validationSemester={null}
              isDragging={active !== null}
              activeIndex={(active !== null && active.semester === classesGrid.length + off) ? active.index : null}
              setActive={setActive}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

interface CardProps {
  title?: string
  imageId: number
}

export const Card = ({
  title = 'Welcome to Our Sample Component',
  imageId
}: CardProps): JSX.Element => {
  return (
    <div className="card-container">
      <img
        src={`https://picsum.photos/id/${imageId}/400/200`}
        alt="Sample"
        className="card-image"
      />
      <h2 className="card-title">{title}</h2>
      <p className="card-paragraph">
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla eget
        libero quam. Fusce efficitur, lectus ac commodo maximus, neque augue
        tincidunt tellus, id dictum odio eros ac nulla.
      </p>
      <p className="card-paragraph">
        Vivamus at urna sit amet justo auctor vestibulum ut nec nisl. Sed auctor
        augue eget libero tincidunt, ut dictum libero facilisis. Phasellus non
        libero at nisi eleifend tincidunt a eget ligula.
      </p>
    </div>
  )
}

export default PlanBoard
