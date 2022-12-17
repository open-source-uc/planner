const SemesterColumn = (props: { semester: number, children: React.ReactNode[] }): JSX.Element => {
  return (
        <div className={'basis-1/12 drop-shadow-xl bg-base-200 rounded-lg overflow-hidden'}>
          <h2 className="mt-1 text-xl text-center">{`Semestre ${props.semester}`}</h2>
          <div className="my-2 divider"></div>
          <div className={'max-h-full overflow-auto'}>
            {props.children}
          </div>
        </div>
  )
}

export default SemesterColumn
