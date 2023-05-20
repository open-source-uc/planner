
import { useDrop } from 'react-dnd'
import { CourseDetails } from '../../../client'

interface SemesterColumnProps {
  semester: number
  addEnd: Function
  children?: React.ReactNode[]
}

const SemesterColumn = ({ semester, addEnd, children }: SemesterColumnProps): JSX.Element => {
  const [dropProps, drop] = useDrop(() => ({
    accept: 'card',
    drop (course: CourseDetails & { semester: number }) {
      addEnd(course)
    },
    collect: monitor => ({
      isOver: !!monitor.isOver()
    })
  }))
  return (
    <div className={'drop-shadow-xl w-[165px] shrink-0 bg-base-200 rounded-lg h-full flex flex-col'}>
      <h2 className="mt-1 text-[1.2rem] text-center">{`Semestre ${semester}`}</h2>
      <div className="my-2 divider"></div>
      <div className={'max-h-full '}>
        {children}
      </div>
      <div ref={drop} className={'px-2 flex min-h-[90px] flex-grow'}>
        {dropProps.isOver &&
            <div className={'bg-place-holder card w-full'} />
        }
      </div>
    </div>
  )
}

export default SemesterColumn
