import { useDrop } from 'react-dnd'
import type { Course } from '../lib/types'

const SemesterColumn = (props: { semester: number, children: React.ReactNode[], handleMove: Function }): JSX.Element => {
  const [, drop] = useDrop(() => ({
    accept: 'card',
    drop (course: Course) {
      props.handleMove(course)
    },
    collect (monitor) {
      return {
        isDragging: monitor
      }
    }
  }))
  return (
        <div ref={drop} className={'p-1 basis-1/12 drop-shadow-xl bg-base-200 rounded-lg overflow-hidden'}>
          <h2 className="mt-1 text-xl">{`Semestre ${props.semester}`}</h2>
          <div className="my-2 divider"></div>
          <div className={' max-h-full p-2 space-y-3 overflow-auto'}>
            {props.children}
          </div>
        </div>
  )
}

export default SemesterColumn
