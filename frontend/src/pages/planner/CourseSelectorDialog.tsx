import { useState, useEffect, Fragment, memo } from 'react'
import { Dialog, Transition, Switch } from '@headlessui/react'
import { DefaultService, type EquivDetails, type CourseOverview, type CourseDetails, type CancelablePromise } from '../../client'
import { Spinner } from '../../components/Spinner'
import { Info } from '../../components/Info'

// TODO: fetch school list from backend
// Existen escuelas en buscacursos que no tienen cursos: 'Acad Inter de Filosofía'
const schoolOptions = ['Acad Inter de Filosofía', 'Actividades Universitarias', 'Actuación', 'Agronomía e Ing. Forestal', 'Antropología', 'Arquitectura', 'Arte', 'Astrofísica', 'Bachillerato', 'CARA', 'Ciencia Política', 'Ciencias Biológicas', 'Ciencias de la Salud', 'College', 'Comunicaciones', 'Construcción Civil', 'Deportes', 'Derecho', 'Desarrollo Sustentable', 'Diseño', 'Economía y Administración', 'Educación', 'Enfermería', 'Escuela de Gobierno', 'Escuela de Graduados', 'Estudios Urbanos', 'Estética', 'Filosofía', 'Física', 'Geografía', 'Historia', 'Ing Matemática y Computacional', 'Ingeniería', 'Ingeniería Biológica y Médica', 'Instituto de Éticas Aplicadas', 'Letras', 'Matemáticas', 'Medicina', 'Medicina Veterinaria', 'Música', 'Odontología', 'Psicología', 'Química', 'Química y Farmacia', 'Requisito Idioma', 'Sociología', 'Teología', 'Trabajo Social', 'Villarrica']
const coursesBatchSize = 30
const semestreApiOptions = [
  [undefined, undefined], // todos los semestres
  [true, undefined], // primeros semestres
  [undefined, true] // segundos semestres
]

interface Filter {
  name: string
  credits: string
  school: string
  available: boolean
  on_semester: number
}

const CourseSelectorDialog = ({ equivalence, open, onClose }: { equivalence?: EquivDetails, open: boolean, onClose: Function }): JSX.Element => {
  const [loadedCourses, setLoadedCourses] = useState<Record<string, CourseOverview>>({})
  const [filteredCodes, setFilteredCodes] = useState<string[]>([])
  const [loadingCoursesData, setLoadingCoursesData] = useState(false)
  const [selectedCourse, setSelectedCourse] = useState<string>()
  const [filter, setFilter] = useState<Filter>(() => ({
    name: '',
    credits: '',
    school: '',
    available: true,
    on_semester: 0
  }))

  const [promiseInstance, setPromiseInstance] = useState<CancelablePromise<any> | null>(null)

  function resetFilters (): void {
    setSelectedCourse(undefined)
    setFilter({
      name: '',
      credits: '',
      school: '',
      available: true,
      on_semester: 0
    })
    if (promiseInstance != null) {
      promiseInstance.cancel()
      setPromiseInstance(null)
      setLoadingCoursesData(false)
    }
  }

  async function getCourseDetails (coursesCodes: string[]): Promise<void> {
    if (coursesCodes.length === 0) return
    setLoadingCoursesData(true)

    const promise = DefaultService.getCourseDetails(coursesCodes)
    setPromiseInstance(promise)
    const response = await promise
    setPromiseInstance(null)

    const dict = response.reduce((acc: Record<string, CourseDetails>, curr: CourseDetails) => {
      acc[curr.code] = curr
      return acc
    }, {})
    setLoadedCourses((prev) => { return { ...prev, ...dict } })
    setLoadingCoursesData(false)
  }

  async function handleSearch (filterProp: Filter): Promise<void> {
    setLoadingCoursesData(true)
    const crd = filterProp.credits === '' ? undefined : parseInt(filterProp.credits)
    const onlyAvaible = filterProp.available ? filterProp.available : undefined
    if (promiseInstance != null) {
      promiseInstance.cancel()
      setPromiseInstance(null)
    }
    if (equivalence === undefined) {
      const promise = DefaultService.searchCourseDetails({
        text: filterProp.name,
        credits: crd,
        school: filterProp.school,
        available: onlyAvaible,
        first_semester: semestreApiOptions[filterProp.on_semester][0],
        second_semester: semestreApiOptions[filterProp.on_semester][1]
      })
      setPromiseInstance(promise)
      const response = await promise
      setPromiseInstance(null)
      const dict = response.flat().reduce((acc: Record<string, CourseOverview>, curr: CourseOverview) => {
        acc[curr.code] = curr
        return acc
      }, {})
      setFilteredCodes(response.flat().reduce((acc: string[], curr: CourseOverview) => {
        acc.push(curr.code)
        return acc
      }, []))
      setLoadedCourses(dict)
      setLoadingCoursesData(false)
    } else {
      const promise = DefaultService.searchCourseCodes({
        text: filterProp.name,
        credits: crd,
        school: filterProp.school,
        available: onlyAvaible,
        first_semester: semestreApiOptions[filterProp.on_semester][0],
        second_semester: semestreApiOptions[filterProp.on_semester][1],
        equiv: equivalence.code
      })
      setPromiseInstance(promise)
      const response = await promise
      setPromiseInstance(null)
      const missingInfo = []
      for (const code of response.flat()) {
        if (missingInfo.length >= coursesBatchSize) break
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
      setFilteredCodes(response.flat())
      setLoadingCoursesData(false)
    }
  }

  const handleScroll: React.EventHandler<React.SyntheticEvent<HTMLTableSectionElement>> = event => {
    if (!open || loadingCoursesData) return
    const { scrollTop, scrollHeight, clientHeight } = event.currentTarget
    if (scrollTop + clientHeight === scrollHeight && equivalence !== undefined) {
      getCourseDetails(filteredCodes.filter((code) => !Object.keys(loadedCourses).includes(code)).splice(0, coursesBatchSize)).catch(err => { console.log(err) })
    }
  }

  const handleKeyDownFilter: React.EventHandler<React.KeyboardEvent<HTMLInputElement>> = e => {
    if (e.key === 'Enter') {
      e.preventDefault()
      try {
        void handleSearch(filter)
      } catch (err) {
        console.log(err)
      }
    }
  }

  const handleKeyDownSelection: React.EventHandler<React.KeyboardEvent<HTMLInputElement>> = e => {
    if (e.key === 'Enter') {
      e.preventDefault()
      try {
        void onClose(selectedCourse)
      } catch (err) {
        console.log(err)
      }
    }
  }

  useEffect(() => {
    const showCoursesCount = Object.keys(loadedCourses).filter(key => filteredCodes.includes(key)).length
    if (showCoursesCount < coursesBatchSize && filteredCodes.length > 0) {
      getCourseDetails(filteredCodes.filter((code) => !Object.keys(loadedCourses).includes(code)).splice(0, coursesBatchSize)).catch(err => { console.log(err) })
    }
  }, [filteredCodes])

  useEffect(() => {
    if (!open) {
      resetFilters()
      setFilteredCodes([])
      setLoadedCourses({})
    } else if (equivalence !== undefined) {
      void handleSearch(filter)
    }
  }, [open])

  return (
    <Transition.Root show={open} as={Fragment}>
    <Dialog as="div" className="modal relative" onClose={() => { setSelectedCourse(undefined); onClose() }}>
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
                  {equivalence !== undefined && equivalence.courses.length < 10 &&
                  <div className="my-auto inline-flex mb-3">
                    <label className="my-auto mr-2" htmlFor="availableFilter">Ocultar cursos no disponibles: </label>
                    <Switch
                      checked={filter.available}
                      onChange={(e: boolean) => {
                        setFilter({ ...filter, available: e })
                        void handleSearch({
                          name: '',
                          credits: '',
                          school: '',
                          available: e,
                          on_semester: 0
                        })
                      }}
                      id="availableFilter"
                      className={`${
                        filter.available ? 'darkBlue' : 'bg-gray-200'
                      } mr-2 relative inline-flex h-6 w-11 items-center rounded-full`}
                    >
                      <span className="sr-only">Ocultar cursos no disponibles</span>
                      <span
                        className={`${
                          filter.available ? 'translate-x-6' : 'translate-x-1'
                        } inline-block h-4 w-4 transform rounded-full bg-white transition`}
                      />
                    </Switch>
                    <Info message="Un curso no disponible es aquel que no se ha dictado recientemente, generalmente porque ya no se ofrece o porque es nuevo y aún no se ha impartido."/>
                  </div>
                  }
                {(equivalence === undefined || equivalence.courses.length >= 10) &&
                  <div className="grid border-2 p-4 py-3 rounded bg-slate-100 border-slate-500 border-solid gap-2 grid-cols-12">
                    <div className="col-span-9 flex">
                      <label className="mr-3 my-auto" htmlFor="nameFilter">Nombre o Sigla: </label>
                      <input className="grow rounded py-1" type="text" id="nameFilter" value={filter.name} onChange={e => { setFilter({ ...filter, name: e.target.value }) }} onKeyDown={handleKeyDownFilter}/>
                    </div>
                    <div className="col-span-3 flex">
                      <label className="mr-3 my-auto" htmlFor="creditsFilter">Creditos: </label>
                      <select className="grow rounded py-1" id="creditsFilter" value={filter.credits} onChange={e => { setFilter({ ...filter, credits: e.target.value }) }}>
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

                    <div className="col-span-8 flex">
                      <label className="mr-3 my-auto" htmlFor="schoolFilter">Escuela: </label>
                      <select className="grow rounded py-1" id="schoolFilter" value={filter.school} onChange={e => { setFilter({ ...filter, school: e.target.value }) }} >
                        <option value=''>-- Todas --</option>
                        {schoolOptions.map(school => <option key={school} value={school}>{school}</option>)}
                      </select>
                    </div>

                    <div className="col-span-4 flex">
                      <label className="mr-3 my-auto" htmlFor="semesterFilter">Semestralidad: </label>
                      <select className="grow rounded py-1" id="semesterFilter" value={filter.on_semester} onChange={e => { setFilter({ ...filter, on_semester: parseInt(e.target.value) }) }}>
                        <option value={0}>Cualquiera</option>
                        <option value={1}>Pares</option>
                        <option value={2}>Impares</option>
                      </select>
                    </div>

                    <div className="my-auto col-span-5 inline-flex">
                      <label className="my-auto mr-2" htmlFor="availableFilter">Ocultar cursos no disponibles: </label>
                      <Switch
                        checked={filter.available}
                        onChange={(e: boolean) => { setFilter({ ...filter, available: e }) }}
                        id="availableFilter"
                        className={`${
                          filter.available ? 'darkBlue' : 'bg-gray-200'
                        } mr-2 relative inline-flex h-6 w-11 items-center rounded-full`}
                      >
                        <span className="sr-only">Ocultar cursos no disponibles</span>
                        <span
                          className={`${
                            filter.available ? 'translate-x-6' : 'translate-x-1'
                          } inline-block h-4 w-4 transform rounded-full bg-white transition`}
                        />
                      </Switch>
                      <Info message="Un curso no disponible es aquel que no se ha dictado recientemente, generalmente porque ya no se ofrece o porque es nuevo y aún no se ha impartido."/>
                    </div>
                    <div className='flex justify-end col-span-4 col-end-13'>
                      <button
                        className="btn mr-2"
                        onClick={() => {
                          resetFilters()
                          if (equivalence !== undefined) {
                            void handleSearch({
                              name: '',
                              credits: '',
                              school: '',
                              available: true,
                              on_semester: 0
                            })
                          }
                        }}>
                          Limpiar Filtros
                      </button>
                      <button className="btn" onClick={() => {
                        try {
                          void handleSearch(filter)
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
                  {Object.entries(loadedCourses).filter(([key, course]) => filteredCodes.includes(key)).map(([code, course], index) => (
                    <tr key={code} className="flex mt-3 mx-3">
                      <td className="w-8">
                        <input
                          className='cursor-pointer'
                          id={code}
                          type="radio"
                          name="status"
                          value={code}
                          onChange={e => { setSelectedCourse(e.target.value) }}
                          onKeyDown={handleKeyDownSelection}
                        />
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
              <div className='right-0'>
                {Object.keys(loadedCourses).filter(key => filteredCodes.includes(key)).length} - {filteredCodes.length}{equivalence === undefined && filteredCodes.length === 50 && '+'}
                <div className='float-right mx-2 inline-flex'>
                  <button className="btn mr-2" onClick={() => onClose()}>Cancelar</button>
                  <div className="group relative flex justify-center">
                    <button
                      className={`btn ${selectedCourse === undefined ? 'cursor-not-allowed opacity-80' : ''}`}
                      onClick={() => onClose(selectedCourse)}
                      disabled={selectedCourse === undefined}
                    >
                      Guardar
                    </button>
                    {selectedCourse === undefined &&
                    <span className={'absolute left-10 -top-5 z-10 transition-all scale-0 group-hover:scale-100'}>
                      <div className="absolute w-4 h-4 bg-gray-800 rotate-45 rounded" />
                      <span className={'absolute rounded -left-[4rem] -top-10 w-36 bg-gray-800 p-2 text-xs text-white text-center'}>
                        Seleccione un curso para continuar
                      </span>
                    </span>
                    }

                  </div>
                </div>
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </div>
    </Dialog>
    </Transition.Root>
  )
}

export default memo(CourseSelectorDialog)
