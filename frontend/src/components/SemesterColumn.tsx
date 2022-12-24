import { useDrop } from 'react-dnd'

const SemesterColumn = (props: { semester: number, addEnd: Function, children?: React.ReactNode[] }): JSX.Element => {
  const [dropProps, drop] = useDrop(() => ({
    accept: 'card',
    drop (course: { code: string, semester: number }) {
      props.addEnd(course)
    },
    collect: monitor => ({
      isOver: !!monitor.isOver()
    })
  }))
  return (
        <div className={'basis-1/12 drop-shadow-xl bg-base-200 rounded-lg overflow-hidden flex flex-col'}>
          <h2 className="mt-1 text-xl text-center">{`Semestre ${props.semester}`}</h2>
          <div className="my-2 divider"></div>
          <div className={'max-h-full overflow-auto'}>
            {props.children}
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
