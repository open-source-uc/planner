
import { useDrop } from 'react-dnd'

const SemesterColumn = ({ semester, addEnd, children }: { semester: number, addEnd: Function, children?: React.ReactNode[] }): JSX.Element => {
  const [dropProps, drop] = useDrop(() => ({
    accept: 'card',
    drop (course: { code: string, semester: number }, monitor) {
      addEnd(course)
    },
    collect: monitor => ({
      isOver: !!monitor.isOver()
    })
  }))
  return (
        <div className={'drop-shadow-xl basis-[12.5%] shrink-0 bg-base-200 rounded-lg'}>
          <h2 className="mt-1 text-xl text-center">{`Semestre ${semester}`}</h2>
          <div className="my-2 divider"></div>
          <div className={'max-h-full '}>
            {children}
          </div>
          <div ref={drop} className={'px-2 flex flex-grow min-h-[60px]'}>
            {dropProps.isOver &&
              <div className={'bg-place-holder card w-full'} />
            }
          </div>
        </div>
  )
}

export default SemesterColumn
