import { useState, useEffect, Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { DefaultService, Equivalence, Course } from '../client'

const CourseSelectorDialog = ({ equivalence, open, onClose }: { equivalence?: Equivalence, open: boolean, onClose: Function }): JSX.Element => {
  const [courses, setCourses] = useState<Course[]>([])
  const [offset, setOffset] = useState(10)
  const [selectedCourse, setSelectedCourse] = useState<string>()
  const [filter, setFilter] = useState({
    name: '',
    code: '',
    credits: -1,
    school: ''
  })

  async function getCourseDetails (coursesCodes: string[]): Promise<void> {
    if (coursesCodes.length === 0) return
    const response = await DefaultService.getCourseDetails(coursesCodes)
    // response = response.filter(course => course.semestrality_first || course.semestrality_second)
    setCourses([...courses, ...response])
  }

  async function handleSearch (): Promise<void> {
    const response = await DefaultService.searchCourses(filter.name, filter.credits, filter.school)
    const codeFilter = response.map(course => course.code)
    console.log(response)
    setCourses(courses.filter(course => course.code in codeFilter))
  }

  const handleScroll: React.EventHandler<React.SyntheticEvent<HTMLTableSectionElement>> = event => {
    const { scrollTop, scrollHeight, clientHeight } = event.currentTarget
    if (scrollTop + clientHeight === scrollHeight && equivalence !== undefined) {
      setOffset(offset + 10)
      getCourseDetails(equivalence.courses.slice(offset, offset + 10)).catch(err => console.log(err))
    }
  }

  useEffect(() => {
    if (!open) { setCourses([]); setOffset(10) } else if (equivalence !== undefined) getCourseDetails(equivalence.courses.slice(0, 10)).catch(err => console.log(err))
  }, [open])

  if (equivalence === undefined) return <></>
  return (
    <Transition.Root show={open} as={Fragment}>
    <Dialog as="div" className="relative z-10" onClose={() => { setSelectedCourse(undefined); onClose() }}>
      <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-100"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>
      <div className="fixed inset-0 overflow-y-auto ">
        <div className="flex items-center min-h-screen justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-200"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-100"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
            <Dialog.Panel className="w-11/12 bg-blue-50 overflow-y-hidden max-w-4xl transform  rounded-2xl border-2 border-gray-900 p-6 text-left align-middle shadow-xl transition-all">
              <Dialog.Title as="h3" className="text-lg font-medium leading-6 text-gray-900">
                {equivalence.name}
              </Dialog.Title>
                {(equivalence.courses.length === 0 || equivalence.courses.length >= 30) &&
                  <div className="grid border-2 p-4 py-3 rounded border-gray-600 border-solid gap-2 grid-cols-5 my-3">
                    <div className="col-span-3 grid  grid-cols-3">
                      <label className="col-span-1 my-auto" htmlFor="nameFilter">Nombre: </label>
                      <input className="col-span-2 rounded py-1" type="text" id="nameFilter" value={filter.name} onChange={e => setFilter({ ...filter, name: e.target.value })} />
                    </div>
                    <div className="col-span-2">
                      <label htmlFor="codeFilter">Sigla: </label>
                      <input className="rounded py-1" type="text" id="codeFilter" value={filter.code} onChange={e => setFilter({ ...filter, code: e.target.value })} />
                    </div>
                    <div className="col-span-3 grid  grid-cols-3">
                      <label className="col-span-1 my-auto" htmlFor="schoolFilter">Unidad academica: </label>
                      <input className="col-span-2 rounded py-1" type="text" id="schoolFilter" value={filter.school} onChange={e => setFilter({ ...filter, school: e.target.value })} />
                    </div>
                    <div className="col-span-2">
                      <label htmlFor="creditsFilter">Creditos: </label>
                      <select className="rounded py-1" id="creditsFilter" value={filter.credits} onChange={e => setFilter({ ...filter, credits: parseInt(e.target.value) })}>
                        <option value={-1}>-</option>
                        <option value={5}>5</option>
                        <option value={10}>10</option>
                        <option value={15}>15</option>
                        <option value={30}>30</option>
                      </select>
                    </div>
                    <div className='flex justify-end col-span-2 col-end-6'>
                      <button className="btn mr-2" onClick={() => setFilter({ name: '', code: '', credits: -1, school: '' })}>Limpiar Filtros</button>
                      <button className="btn" onClick={async () => await handleSearch()}>Buscar</button>
                    </div>
                  </div>
                }
              <table className="text-left table-auto mb-3 p-3  w-full box-border">
                <thead>
                  <tr className="border-b-2 border-gray-600 flex w-full">
                    <th className="w-8"></th>
                    <th className="w-20">Sigla</th>
                    <th className="w-96">Nombre</th>
                    <th className="w-8">Crd</th>
                    <th className="w-52">Unidad Academica</th>
                    <th className="w-6"></th>
                  </tr>
                </thead>
                <tbody onScroll={handleScroll} className="bg-white flex flex-col items-center justify-between overflow-y-scroll max-h-72 pt-2">
                {courses.map((course: Course) => (
                  <tr key={course.code} className="flex mb-3">
                    <td className="w-8">
                      <input className='ml-1' id={course.code} type="radio" name="status" value={course.code} onChange={e => setSelectedCourse(e.target.value)}/>
                    </td>
                    <td className='w-20'>{course.code}</td>
                    <td className='w-96'>{course.name}</td>
                    <td className='w-8'>{course.credits}</td>
                    <td className='w-52'>{course.school}</td>
                    <th className="w-8"></th>
                  </tr>
                ))}</tbody>
              </table>
              <div className='right-0'>{courses.length} - {equivalence.courses.length}</div>
              <div className='float-right mx-2 '>
                <button className="btn mr-2" onClick={() => onClose()}>Cancelar</button>
                <button className="btn " onClick={() => onClose(selectedCourse)}>Guardar</button>
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </div>
    </Dialog>
    </Transition.Root>
  )
}

export default CourseSelectorDialog
