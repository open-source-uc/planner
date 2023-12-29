import { useState } from 'react'
import { type CoursePos, type PseudoCourseId } from '../utils/Types'
import { type EquivDetails } from '../../../client'

interface CoursesContextMenuProps {
  posibleBlocks: EquivDetails[]
  points: { x: number, y: number }
  coursePos?: CoursePos
  courseInfo: {
    code: string
    instance: number
    credits: number
    isEquivalence: boolean
  }
  setClicked: Function
  courseDetails?: PseudoCourseId
  remCourse: Function
  forceBlockChange: Function
}

const CoursesContextMenu = ({ posibleBlocks, points, courseInfo, setClicked, courseDetails, coursePos, remCourse, forceBlockChange }: CoursesContextMenuProps): JSX.Element => {
  const [showBlocks, setShowBlocks] = useState(false)
  const [showMoreInfo, setShowMoreBlocks] = useState(false)

  return (
    <div id="context-menu" className="z-50 absolute w-40 bg-slate-100 border-slate-300 border-2  box-border" style={{ top: points.y, left: points.x }}>
    <ul className="box-border m-0 list-none font-medium text-sm text-gray-900 ">
      {courseDetails?.is_concrete === true && (
      <div
        className="block p-2 w-full text-left hover:cursor-pointer hover:bg-slate-200 border-slate-300"
        onMouseEnter={() => { setShowMoreBlocks(true) }}
        onMouseLeave={() => { setShowMoreBlocks(false) }}
      >Mas información
      {showMoreInfo && (
        <div className="w-44 absolute top-0 left-full bg-slate-100 border-slate-300 border-2  shadow-md">
          <a
            className="block w-full p-2 text-left hover:bg-slate-200"
            href={`https://catalogo.uc.cl/index.php?tmpl=component&option=com_catalogo&view=programa&sigla=${courseInfo.code}`} rel="noreferrer" target="_blank"
          >Ver programa</a>
          <a
            className="block w-full p-2 text-left hover:bg-slate-200  border-t-2 border-slate-200"
            href={`https://catalogo.uc.cl/index.php?tmpl=component&option=com_catalogo&view=requisitos&sigla=${courseInfo.code}`} rel="noreferrer" target="_blank"
          >Ver requisitos</a>
          <a
            className="block w-full p-2 text-left hover:bg-slate-200  border-t-2 border-slate-200"
            href={`https://buscacursos.uc.cl/?cxml_sigla=${courseInfo.code}`} rel="noreferrer" target="_blank"
          >Ver en busca cursos</a>
        </div>
      )}
      </div>
      )}

      {posibleBlocks.length > 0 && (
        <div
          className="p-2 relative w-full text-left hover:cursor-pointer hover:bg-slate-200 border-t-2 border-slate-300"
          onMouseEnter={() => { setShowBlocks(true) }}
          onMouseLeave={() => { setShowBlocks(false) }}
        >
          Ver bloques posibles
          {showBlocks && (
            <div className="w-44 absolute top-0 left-full bg-slate-100 border-slate-300 border-2  shadow-md">
              {posibleBlocks.map((block, index) => (
                <button
                  key={index}
                  className={`block w-full p-2 text-left hover:bg-slate-300 ${courseDetails !== undefined && 'equivalence' in courseDetails && block.code === courseDetails.equivalence?.code ? 'bg-slate-200' : ''}`}
                  onClick={() => {
                    if (courseDetails !== undefined && 'equivalence' in courseDetails && block.code === courseDetails.equivalence?.code) return
                    forceBlockChange(block.code, coursePos, courseInfo.credits)
                  }}
                >
                  {block.name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      <button
        id="delete-course"
        className="p-2 w-full text-left hover:cursor-pointer hover:bg-slate-200 border-t-2 border-slate-300"
        onClick={() => {
          remCourse(courseInfo)
          setClicked(false)
        }}
      >Eliminar</button>
    </ul>
  </div>
  )
}

export default CoursesContextMenu
