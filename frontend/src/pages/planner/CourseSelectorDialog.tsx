import { useState, useEffect, Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { DefaultService, Equivalence, Course } from '../../client'
import { Spinner } from '../../components/Spinner'

// 'Acad Inter de Filosofía': Escuela que sale en buscacursos pero no tiene cursos  (ta raro)
const schoolOptions = ['Actividades Universitarias', 'Actuación', 'Agronomía e Ing. Forestal', 'Antropología', 'Arquitectura', 'Arte', 'Astrofísica', 'Bachillerato', 'CARA', 'Ciencia Política', 'Ciencias Biológicas', 'Ciencias de la...Ingeniería Biológica y Médica', 'Instituto de Éticas Aplicadas', 'Letras', 'Matemáticas', 'Medicina', 'Medicina Veterinaria', 'Música', 'Odontología', 'Psicología', 'Química', 'Química y Farmacia', 'Requisito Idioma', 'Sociología', 'Teología', 'Villarrica', 'Trabajo Social']

const CourseSelectorDialog = ({ equivalence, open, onClose }: { equivalence?: Equivalence, open: boolean, onClose: Function }): JSX.Element => {
  const [loadedCourses, setLoadedCourses] = useState<Course[]>([])
  const [loadingCoursesData, setLoadingCoursesData] = useState(false)
  const [offset, setOffset] = useState(0)
  const [selectedCourse, setSelectedCourse] = useState<string>()
  const [filter, setFilter] = useState({
    name: '',
    credits: '',
    school: '',
    isfiltering: false
  })

  async function resetFilters (): Promise<void> {
    if (!filter.isfiltering && open) return
    setFilter({
      name: '',
      credits: '',
      school: '',
      isfiltering: false
    })
    setOffset(0)
    if (equivalence !== undefined && open) {
      const response = await DefaultService.getCourseDetails(equivalence.courses.slice(0, 10))
      setLoadedCourses(response)
    } else {
      setLoadedCourses([])
    }
  }

  async function getCourseDetails (coursesCodes: string[], offset: number): Promise<void> {
    if (coursesCodes.length === 0 || loadingCoursesData || offset >= coursesCodes.length) return
    setLoadingCoursesData(true)
    let response = await DefaultService.getCourseDetails(coursesCodes.slice(offset, offset + 20))
    response = response.filter(course => course.semestrality_first || course.semestrality_second)
    offset = offset + 20
    while (response.length < 10 && offset < coursesCodes.length) {
      const newResponse = await DefaultService.getCourseDetails(coursesCodes.slice(offset, offset + 20))
      offset += 20
      response = [...response, ...newResponse]
    }
    setLoadedCourses(prev => [...prev, ...response])
    setOffset(offset)
    setLoadingCoursesData(false)
  }

  async function handleSearch (): Promise<void> {
    setLoadingCoursesData(true)
    if (filter.name !== '' || filter.credits !== '' || filter.school !== '') {
      setFilter({ ...filter, isfiltering: true })
    } else {
      setFilter({ ...filter, isfiltering: false })
    }
    const crd = filter.credits === '' ? undefined : parseInt(filter.credits)
    const response = await DefaultService.searchCourses(filter.name, crd, filter.school)
    const codeFilter = response.map(course => course.code)
    if (codeFilter.length === 0) {
      setLoadingCoursesData(false)
      setLoadedCourses([])
      return
    }
    const coursesDet = await DefaultService.getCourseDetails(codeFilter)
    setLoadedCourses(coursesDet.filter(course => course.semestrality_first || course.semestrality_second))
    setLoadingCoursesData(false)
  }

  const handleScroll: React.EventHandler<React.SyntheticEvent<HTMLTableSectionElement>> = event => {
    if (filter.isfiltering || !open) return
    const { scrollTop, scrollHeight, clientHeight } = event.currentTarget
    if (scrollTop + clientHeight === scrollHeight && equivalence !== undefined) {
      getCourseDetails(equivalence.courses, offset).catch(err => console.log(err))
    }
  }

  useEffect(() => {
    if (!open) { void resetFilters() } else if (equivalence !== undefined) {
      getCourseDetails(equivalence.courses, offset).catch(err => console.log(err))
    }
  }, [open])

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
            <Dialog.Panel className="w-11/12 px-5 py-6 bg-slate-100 border-slate-300 overflow-y-hidden max-w-4xl transform  rounded-2xl border-2 text-left align-middle shadow-xl transition-all">
              <Dialog.Title as="h3" className="text-lg font-medium leading-6 text-gray-900">
                {equivalence !== undefined ? equivalence.name : 'Curso Extra'}
              </Dialog.Title>
                {(equivalence === undefined || equivalence.courses.length >= 30) &&
                  <div className="grid border-2 p-4 py-3 rounded bg-slate-100 border-slate-500 border-solid gap-2 grid-cols-5 my-3">
                    <div className="col-span-5 grid  grid-cols-5">
                      <label className="col-span-1 my-auto" htmlFor="nameFilter">Nombre o Sigla: </label>
                      <input className="col-span-4 rounded py-1" type="text" id="nameFilter" value={filter.name} onChange={e => setFilter({ ...filter, name: e.target.value })} />
                    </div>
                    <div className="col-span-4 grid  grid-cols-4">
                      <label className="col-span-1 my-auto" htmlFor="schoolFilter">Escuela: </label>
                      <select className="col-span-3 rounded py-1" id="schoolFilter" value={filter.school} onChange={e => setFilter({ ...filter, school: e.target.value })} >
                        <option value=''>-- Todas --</option>
                        {schoolOptions.map(school => <option key={school} value={school}>{school}</option>)}
                      </select>
                    </div>
                    <div className="col-span-1 col-end-6 ">
                      <label htmlFor=" creditsFilter">Creditos: </label>
                      <select className="rounded py-1" id="creditsFilter" value={filter.credits} onChange={e => setFilter({ ...filter, credits: e.target.value })}>
                        <option value={''}>-</option>
                        <option value={'5'}>5</option>
                        <option value={'10'}>10</option>
                        <option value={'15'}>15</option>
                        <option value={'30'}>30</option>
                      </select>
                    </div>
                    <div className='flex justify-end col-span-2 col-end-6'>
                      <button className="btn mr-2" onClick={async () => await resetFilters()}>Limpiar Filtros</button>
                      <button className="btn" onClick={async () => await handleSearch()}>Buscar</button>
                    </div>
                  </div>
                }
              <table className="text-left table-auto mb-3 p-3  w-full box-border">
                <thead className="items-center justify-between">
                  <tr className="border-b-2 border-slate-500 flex w-full">
                    <th className="w-8"></th>
                    <th className="w-20">Sigla</th>
                    <th className="w-96">Nombre</th>
                    <th className="w-8">Crd</th>
                    <th className="w-52">Escuela</th>
                    <th className="w-6"></th>
                  </tr>
                </thead>
                <tbody onScroll={handleScroll} className="bg-white relative rounded-b flex flex-col items-center justify-between overflow-y-scroll h-72 pt-2">
                {loadedCourses.map((course: Course) => (
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
                ))}
                {loadingCoursesData && (
                  <tr>
                    <td className="bg-white flex absolute top-0 left-0 bottom-0 right-0"> <Spinner message='Cargando cursos...' /></td>
                  </tr>
                )}
                </tbody>
              </table>
              <div className='right-0'>{loadedCourses.length} Cursos cargados</div>
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
