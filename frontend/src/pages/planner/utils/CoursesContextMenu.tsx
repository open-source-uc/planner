import { useState } from 'react'
import { type CoursePos, type PseudoCourseId } from '../utils/Types'
import { type EquivDetails } from '../../../client'

interface CoursesContextMenuProps {
  posibleBlocks: EquivDetails[]
  points: { x: number, y: number }
  isEquivalence: boolean
  coursePos?: CoursePos
  courseInfo?: PseudoCourseId
  openEquivModal: Function
  forceBlockChange: Function
}

const CoursesContextMenu = ({ posibleBlocks, points, isEquivalence, courseInfo, coursePos, openEquivModal, forceBlockChange }: CoursesContextMenuProps): JSX.Element => {
  const [showBlocks, setShowBlocks] = useState(false)

  return (
    <div className="z-50 absolute w-40 bg-slate-100 border-slate-300 border-2 rounded-md box-border" style={{ top: points.y, left: points.x }}>
    <ul className="box-border m-0 list-none font-medium text-sm text-gray-900 ">
      {courseInfo?.is_concrete === true && (
      <a
        className="block p-2 w-full text-left hover:cursor-pointer hover:bg-slate-200 border-slate-300"
        href={`https://catalogo.uc.cl/index.php?tmpl=component&option=com_catalogo&view=programa&sigla=${courseInfo.code}`} rel="noreferrer" target="_blank"
      >Mas información</a>
      )}
      {isEquivalence && (
        <button
          className="p-2 w-full text-left hover:cursor-pointer hover:bg-slate-200 border-t-2 border-slate-300"
          onClick={() => {
            if (coursePos !== undefined && courseInfo !== undefined) {
              if ('equivalence' in courseInfo && courseInfo.equivalence !== undefined) {
                void openEquivModal(courseInfo.equivalence, coursePos.semester, coursePos.index)
              } else {
                void openEquivModal(courseInfo, coursePos.semester, coursePos.index)
              }
            }
          }}
        >Ver equivalencias</button>
      )}
      {posibleBlocks.length > 0 && (
        <div
          className="p-2 relative w-full text-left hover:cursor-pointer hover:bg-slate-200 border-t-2 border-slate-300"
          onMouseEnter={() => { setShowBlocks(true) }}
          onMouseLeave={() => { setShowBlocks(false) }}
        >
          Ver bloques posibles
          {showBlocks && (
            <div className="w-44 absolute top-0 left-full bg-slate-100 border-slate-300 border-2  rounded-md shadow-md">
              {posibleBlocks.map((block, index) => (
                <button
                  key={index}
                  className={`block w-full p-2 text-left hover:bg-slate-200 ${courseInfo !== undefined && 'equivalence' in courseInfo && block.code === courseInfo.equivalence?.code ? 'bg-slate-200' : ''}`}
                  onClick={() => {
                    if (courseInfo !== undefined && 'equivalence' in courseInfo && block.code === courseInfo.equivalence?.code) return
                    forceBlockChange(block.code)
                  }}
                >
                  {block.name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </ul>
  </div>
  )
}

export default CoursesContextMenu
