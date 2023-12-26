import { useState, useEffect, memo, useRef, useCallback } from 'react'
import { Dialog, Switch } from '@headlessui/react'
import { DefaultService, type EquivDetails, type CourseOverview, type CourseDetails, type CancelablePromise } from '../../../client'
import { Spinner } from '../../../components/Spinner'
import { Info } from '../../../components/Info'
import { type PseudoCourseDetail, isCancelError } from '../utils/Types'
import GeneralModal from '../../../components/GeneralModal'

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
  const acceptButton = useRef<HTMLButtonElement>(null)
  const creditsInputRef = useRef<HTMLSelectElement>(null)
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
  const [nameForm, setNameForm] = useState<string>('')
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [, setPromiseInstance] = useState<CancelablePromise<any> | null>(null)

  const resetFilters = useCallback((): void => {
    setSelectedCourse(undefined)
    setFilter({
      name: '',
      credits: '',
      school: '',
      available: true,
      on_semester: 0
    })
    setNameForm('')
    setPromiseInstance(prev => {
      if (prev != null) {
        prev.cancel()
        return null
      }
      return prev
    })
    setLoadingCoursesData(prev => {
      if (!prev) {
        return false
      }
      return prev
    })
  }, [])

  const close = useCallback((): void => {
    resetFilters()
    setFilteredCodes([])
    setLoadedCourses({})
  }, [resetFilters])

  async function getCourseDetails (coursesCodes: string[]): Promise<void> {
    try {
      if (coursesCodes.length === 0) return
      setLoadingCoursesData(true)

      const promise = DefaultService.getPseudocourseDetails({ codes: coursesCodes })
      setPromiseInstance(promise)
      const response = await promise
      setPromiseInstance(null)

      const dict = response.reduce((acc: Record<string, CourseDetails>, curr: PseudoCourseDetail) => {
        if (!('credits' in curr)) {
          throw new Error('expected only concrete courses in equivalence')
        }
        acc[curr.code] = curr
        return acc
      }, {})
      setLoadedCourses((prev) => { return { ...prev, ...dict } })
    } catch (err) {
      if (!isCancelError(err)) {
        console.error(err)
      }
    }
    setLoadingCoursesData(false)
  }

  const handleSearch = useCallback(async (equivalence?: EquivDetails, filterProp: Filter = {
    name: '',
    credits: '',
    school: '',
    available: true,
    on_semester: 0
  }, loadedCourses?: Record<string, CourseOverview>): Promise<void> => {
    setLoadingCoursesData(true)
    const crd = filterProp.credits === '' ? undefined : parseInt(filterProp.credits)
    const onlyAvaible = filterProp.available ? filterProp.available : undefined
    if (equivalence === undefined) {
      const promise = DefaultService.searchCourseDetails({
        text: filterProp.name,
        credits: crd,
        school: filterProp.school,
        available: onlyAvaible,
        first_semester: semestreApiOptions[filterProp.on_semester][0],
        second_semester: semestreApiOptions[filterProp.on_semester][1]
      })
      setPromiseInstance(prev => {
        if (prev != null) {
          prev.cancel()
        }
        return promise
      })
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
      setPromiseInstance(prev => {
        if (prev != null) {
          prev.cancel()
        }
        return promise
      })
      const response = await promise
      setPromiseInstance(null)
      const missingInfo = []
      for (const code of response.flat()) {
        if (missingInfo.length >= coursesBatchSize) break
        if (loadedCourses !== undefined && code in loadedCourses) continue
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
  }, [])

  const handleScroll: React.EventHandler<React.SyntheticEvent<HTMLTableSectionElement>> = event => {
    if (!open || loadingCoursesData) return
    const { scrollTop, scrollHeight, clientHeight } = event.currentTarget
    if (scrollTop + clientHeight === scrollHeight && equivalence !== undefined) {
      getCourseDetails(filteredCodes.filter((code) => !Object.keys(loadedCourses).includes(code)).splice(0, coursesBatchSize)).catch(err => { console.log(err) })
    }
  }

  const handleKeyDownSelection: React.KeyboardEventHandler<HTMLInputElement> = e => {
    if (e.key === 'Enter') {
      e.preventDefault()
      setSelectedCourse(prev => {
        if ('value' in e.target && prev !== e.target.value) {
          return e.target.value as string
        } else {
          return undefined
        }
      })
      acceptButton.current?.focus()
    }
  }

  const handleKeyDownSwitch: React.KeyboardEventHandler<HTMLButtonElement> = e => {
    if (e.key === 'Enter') {
      e.preventDefault()
      setFilter(prev => { return { ...filter, available: !prev.available } })
    }
  }

  const handleKeyDownName: React.KeyboardEventHandler<HTMLInputElement> = e => {
    if (e.key === 'Enter') {
      e.preventDefault()
      creditsInputRef.current?.focus()
    }
  }

  useEffect(() => {
    const showCoursesCount = Object.keys(loadedCourses).filter(key => filteredCodes.includes(key)).length
    if (showCoursesCount < coursesBatchSize && filteredCodes.length > 0) {
      getCourseDetails(filteredCodes.filter((code) => !Object.keys(loadedCourses).includes(code)).splice(0, coursesBatchSize)).catch(err => { console.log(err) })
    }
  }, [filteredCodes, loadedCourses])

  useEffect(() => {
    if (open) {
      void handleSearch(equivalence, filter)
    }
  }, [open, handleSearch, equivalence, filter])

  useEffect(() => {
    // The text input should not update the filter inmediately, but after the user stops typing
    if (open && nameForm !== filter.name) {
      if (debounceTimerRef?.current !== null) {
        clearTimeout(debounceTimerRef.current)
      }
      debounceTimerRef.current = setTimeout(() => {
        setFilter({ ...filter, name: nameForm })
      }, 500)
    }
  }, [open, nameForm, filter])

  return (
    <GeneralModal
      isOpen={open}
      onClose={close}
      initialFocus={acceptButton}
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
                  }}
                  onKeyDown={handleKeyDownSwitch}
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
                  <input className="grow rounded py-1" type="text" id="nameFilter" value={nameForm} onChange={e => { setNameForm(e.target.value) }} onKeyDown={handleKeyDownName}/>
                </div>
                <div className="col-span-3 flex">
                  <label className="mr-3 my-auto" htmlFor="creditsFilter">Creditos: </label>
                  <select className="grow rounded py-1" id="creditsFilter" value={filter.credits} ref={creditsInputRef} onChange={e => { setFilter({ ...filter, credits: e.target.value }) }}>
                    <option value={''}>-</option>
                    <option value={'5'}>5</option>
                    <option value={'10'}>10</option>
                    <option value={'15'}>15</option>
                    <option value={'20'}>20</option>
                  </select>
                </div>

                <div className="col-span-8 flex">
                  <label className="mr-3 my-auto" htmlFor="schoolFilter">Escuela: </label>
                  <select className="grow rounded py-1" id="schoolFilter" value={filter.school} onChange={e => { setFilter({ ...filter, school: e.target.value }) }}>
                    <option value=''>-- Todas --</option>
                    {schoolOptions.map(school => <option key={school} value={school}>{school}</option>)}
                  </select>
                </div>

                <div className="col-span-4 flex">
                  <label className="mr-3 my-auto" htmlFor="semesterFilter">Semestralidad: </label>
                  <select className="grow rounded py-1" id="semesterFilter" value={filter.on_semester} onChange={e => { setFilter({ ...filter, on_semester: parseInt(e.target.value) }) }}>
                    <option value={0}>Cualquiera</option>
                    <option value={1}>Impares</option>
                    <option value={2}>Pares</option>
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
                    onKeyDown={handleKeyDownSwitch}
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
                <div className='flex justify-end col-span-3 col-end-13'>
                  <button
                    className="btn"
                    onClick={() => {
                      resetFilters()
                    }}>
                      Limpiar Filtros
                  </button>
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
                        <td>
                         <label htmlFor={code} className="flex cursor-pointer">
                          <div className="w-8">
                          <input
                            className='cursor-pointer rounded-full'
                            id={code}
                            type="checkbox"
                            name="status"
                            value={code}
                            checked={selectedCourse !== undefined && selectedCourse === code}
                            onChange={e => {
                              setSelectedCourse(prev => {
                                if (prev !== code) {
                                  return code
                                } return undefined
                              })
                            }}
                            onKeyDown={handleKeyDownSelection}
                          />
                          </div>
                          <div className='w-20'>{code}</div>
                          <div className='w-96'>{course.name}</div>
                          <div className='w-8'>{course.credits}</div>
                          <div className='w-52'>{course.school}</div>
                          <div className="w-8"></div>
                        </label>
                        </td>
                      </tr>
                  ))}
                 </tbody>
              </table>
              <div className='right-0'>
                {Object.keys(loadedCourses).filter(key => filteredCodes.includes(key)).length} - {filteredCodes.length}{equivalence === undefined && filteredCodes.length === 50 && '+'}
                <div className='float-right mx-2 inline-flex'>
                  <button className="btn mr-2" onClick={() => { close(); onClose() }}>Cancelar</button>
                  <div className="group relative flex justify-center">
                    <button
                      ref={acceptButton}
                      className={`btn ${selectedCourse === undefined ? 'cursor-not-allowed opacity-80' : ''}`}
                      onClick={() => {
                        if (selectedCourse !== undefined) {
                          onClose(loadedCourses[selectedCourse])
                        } else {
                          onClose()
                        }
                        close()
                      }}
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
          </GeneralModal>
  )
}

export default memo(CourseSelectorDialog)
