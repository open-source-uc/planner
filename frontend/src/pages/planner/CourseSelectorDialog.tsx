import { useState, useEffect, Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { DefaultService, EquivDetails, CourseOverview, CancelablePromise } from '../../client'
import { Spinner } from '../../components/Spinner'

// TODO: fetch school list from backend
// Existen escuelas en buscacursos que no tienen cursos: 'Acad Inter de Filosofía'
const schoolOptions = ['Acad Inter de Filosofía', 'Actividades Universitarias', 'Actuación', 'Agronomía e Ing. Forestal', 'Antropología', 'Arquitectura', 'Arte', 'Astrofísica', 'Bachillerato', 'CARA', 'Ciencia Política', 'Ciencias Biológicas', 'Ciencias de la Salud', 'College', 'Comunicaciones', 'Construcción Civil', 'Deportes', 'Derecho', 'Desarrollo Sustentable', 'Diseño', 'Economía y Administración', 'Educación', 'Enfermería', 'Escuela de Gobierno', 'Escuela de Graduados', 'Estudios Urbanos', 'Estética', 'Filosofía', 'Física', 'Geografía', 'Historia', 'Ing Matemática y Computacional', 'Ingeniería', 'Ingeniería Biológica y Médica', 'Instituto de Éticas Aplicadas', 'Letras', 'Matemáticas', 'Medicina', 'Medicina Veterinaria', 'Música', 'Odontología', 'Psicología', 'Química', 'Química y Farmacia', 'Requisito Idioma', 'Sociología', 'Teología', 'Trabajo Social', 'Villarrica']

const CourseSelectorDialog = ({ equivalence, open, onClose }: { equivalence?: EquivDetails, open: boolean, onClose: Function }): JSX.Element => {
  const [loadedCourses, setLoadedCourses] = useState<{ [code: string]: CourseOverview }>({})
  const [filteredCodes, setFilteredCodes] = useState<string[]>([])
  const [loadingCoursesData, setLoadingCoursesData] = useState(false)
  const [selectedCourse, setSelectedCourse] = useState<string>()
  const [filter, setFilter] = useState(() => ({
    name: '',
    credits: '',
    school: ''
  }))
  const [promiseInstance, setPromiseInstance] = useState<CancelablePromise<any> | null>(null)

  function resetFilters (): void {
    setSelectedCourse(undefined)
    setFilter({
      name: '',
      credits: '',
      school: ''
    })
    if (promiseInstance != null) {
      promiseInstance.cancel()
      setPromiseInstance(null)
    }
    if (equivalence !== undefined && open) {
      setFilteredCodes(equivalence.courses)
    } else {
      setFilteredCodes([])
    }
  }

  async function getCourseDetails (coursesCodes: string[]): Promise<void> {
    if (coursesCodes.length === 0) return
    setLoadingCoursesData(true)

    const promise = DefaultService.getCourseDetails(coursesCodes)
    setPromiseInstance(promise)
    const response = await promise
    setPromiseInstance(null)

    const dict = response.reduce((acc: { [code: string]: CourseOverview }, curr: CourseOverview) => {
      acc[curr.code] = curr
      return acc
    }, {})
    setLoadedCourses((prev) => { return { ...prev, ...dict } })
    setLoadingCoursesData(false)
  }

  async function handleSearch (): Promise<void> {
    setLoadingCoursesData(true)
    const crd = filter.credits === '' ? undefined : parseInt(filter.credits)
    if (promiseInstance != null) promiseInstance.cancel()
    if (equivalence === undefined) {
      const promise = DefaultService.searchCourseDetails({
        text: filter.name,
        credits: crd,
        school: filter.school,
        available: true
      })
      setPromiseInstance(promise)
      const response = await promise
      setPromiseInstance(null)
      const dict = response.reduce((acc: { [code: string]: CourseOverview }, curr: CourseOverview) => {
        acc[curr.code] = curr
        return acc
      }, {})
      setFilteredCodes(response.reduce((acc: string[], curr: CourseOverview) => {
        acc.push(curr.code)
        return acc
      }, []))
      setLoadedCourses(dict)
      setLoadingCoursesData(false)
    } else {
      const promise = DefaultService.searchCourseCodes({
        text: filter.name,
        credits: crd,
        school: filter.school,
        available: true,
        equiv: equivalence.code
      })
      setPromiseInstance(promise)
      const response = await promise
      setPromiseInstance(null)
      const missingInfo = []
      for (const code of response) {
        if (missingInfo.length >= 20) break
        if (code in loadedCourses) continue
        missingInfo.push(code)
      }
      if (missingInfo.length > 0) {
        try {
          await getCourseDetails(missingInfo)
        } catch (e) {
          console.error(e)
        }
      }
      setFilteredCodes(response)
      setLoadingCoursesData(false)
    }
  }

  const handleScroll: React.EventHandler<React.SyntheticEvent<HTMLTableSectionElement>> = event => {
    if (!open || loadingCoursesData) return
    const { scrollTop, scrollHeight, clientHeight } = event.currentTarget
    if (scrollTop + clientHeight === scrollHeight && equivalence !== undefined) {
      getCourseDetails(filteredCodes.filter((code) => !Object.keys(loadedCourses).includes(code)).splice(0, 20)).catch(err => console.log(err))
    }
  }

  useEffect(() => {
    const showCoursesCount = Object.keys(loadedCourses).filter(key => filteredCodes.includes(key)).length
    if (showCoursesCount < 10 && filteredCodes.length > 0) {
      getCourseDetails(filteredCodes.filter((code) => !Object.keys(loadedCourses).includes(code)).splice(0, 20)).catch(err => console.log(err))
    }
  }, [filteredCodes])

  useEffect(() => {
    if (!open) {
      if (promiseInstance != null) { promiseInstance.cancel(); setPromiseInstance(null); setLoadingCoursesData(false) }
      void resetFilters()
      setLoadedCourses({})
    } else if (equivalence !== undefined) {
      setFilteredCodes(equivalence.courses)
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
      <div className="fixed inset-0 overflow-y-auto">
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
            <Dialog.Panel className="w-11/12 px-5 py-6 bg-slate-100 border-slate-300 overflow-hidden max-w-4xl transform  rounded-2xl border-2 text-left align-middle shadow-xl transition-all">
              <Dialog.Title as="h3" className="text-lg font-medium leading-6 text-gray-900  mb-3">
                {equivalence !== undefined ? equivalence.name : 'Curso Extra'}
              </Dialog.Title>
                {(equivalence === undefined || equivalence.courses.length >= 30) &&
                  <div className="grid border-2 p-4 py-3 rounded bg-slate-100 border-slate-500 border-solid gap-2 grid-cols-5">
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
                    <div className="col-span-1 grid grid-cols-2">
                      <label className="col-span-1 my-auto" htmlFor="creditsFilter">Creditos: </label>
                      <select className="col-span-1 col-end-3 rounded py-1" id="creditsFilter" value={filter.credits} onChange={e => setFilter({ ...filter, credits: e.target.value })}>
                        <option value={''}>-</option>
                        <option value={'4'}>4</option>
                        <option value={'5'}>5</option>
                        <option value={'6'}>6</option>
                        <option value={'8'}>8</option>
                        <option value={'10'}>10</option>
                        <option value={'15'}>15</option>
                        <option value={'20'}>20</option>
                        <option value={'30'}>30</option>
                      </select>
                    </div>
                    <div className='flex justify-end col-span-2 col-end-6 '>
                      <button
                        className="btn mr-2"
                        onClick={() => resetFilters()}>
                          Limpiar Filtros
                      </button>
                      <button className="btn" onClick={() => {
                        try {
                          void handleSearch()
                        } catch (err) {
                          console.log(err)
                        }
                      }}>Buscar</button>
                    </div>
                  </div>
                }
              <table className="text-left table-fixed mb-3 p-3  w-full box-border">
                <thead className="items-center justify-between mx-3">
                  <tr className="border-b-2 border-slate-500 block w-full px-3">
                    <th className="w-8"></th>
                    <th className="w-20">Sigla</th>
                    <th className="w-96">Nombre</th>
                    <th className="w-8">Crd</th>
                    <th className="w-52">Escuela</th>
                    <th className="w-8"></th>
                  </tr>
                </thead>
                <tbody onScroll={handleScroll} className="bg-white relative rounded-b block flex-col items-center justify-between overflow-y-scroll h-72 w-full">
                  {loadingCoursesData &&
                  <tr className="fixed pr-10" style={{ height: 'inherit', width: 'inherit' }}><td className="bg-white w-full h-full flex "> <Spinner message='Cargando cursos...' /></td></tr>
                  }
                  {Object.entries(loadedCourses).filter(([key, course]) => filteredCodes.includes(key)).map(([code, course]) => (
                    <tr key={code} className="flex mt-3 mx-3">
                      <td className="w-8">
                        <input className='cursor-pointer' id={code} type="radio" name="status" value={code} onChange={e => setSelectedCourse(e.target.value)}/>
                      </td>
                      <td className='w-20'>{code}</td>
                      <td className='w-96'>{course.name}</td>
                      <td className='w-8'>{course.credits}</td>
                      <td className='w-52'>{course.school}</td>
                      <th className="w-8"></th>
                    </tr>
                  ))}
                 </tbody>
              </table>
              <div className='right-0'>{Object.keys(loadedCourses).filter(key => filteredCodes.includes(key)).length} - {filteredCodes.length}{equivalence === undefined && filteredCodes.length === 50 && '+'}</div>
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
