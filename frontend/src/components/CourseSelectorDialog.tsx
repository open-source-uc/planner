import { useState, useEffect } from 'react'
import { Dialog } from '@headlessui/react'
import { DefaultService, Equivalence, Course } from '../client'

const CourseSelectorDialog = ({ equivalence, open, onClose }: { equivalence?: Equivalence, open: boolean, onClose: Function }): JSX.Element => {
  const [courses, setCourses] = useState<Course[]>([])
  const [offset, setOffset] = useState(10)
  const [selectedCourse, setSelectedCourse] = useState<string>()

  async function getCourseDetails (coursesCodes: string[]): Promise<void> {
    if (coursesCodes.length === 0) return
    const response = await DefaultService.getCourseDetails(coursesCodes)
    // response = response.filter(course => course.semestrality_first || course.semestrality_second)
    setCourses([...courses, ...response])
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
    <Dialog as="div" className="relative z-10" open={open} onClose={() => { setSelectedCourse(undefined); onClose() }}>
      <div className="fixed inset-0 overflow-y-auto ">
        <div className="flex items-center min-h-screen justify-center p-4 text-center">
          <Dialog.Panel className=" w-11/12 bg-blue-50 overflow-y-hidden max-w-4xl transform  rounded-2xl border border-indigo-900 p-6 text-left align-middle shadow-xl transition-all">
            <Dialog.Title as="h3" className="text-lg font-medium leading-6 text-gray-900">
              {equivalence.name}
            </Dialog.Title>
            <table className="text-left table-auto mb-3 p-3 mx-3 w-full">
              <thead className="w-full">
                <tr className="border-b-2 border-gray-600 flex w-full">
                  <th className="w-8"></th>
                  <th className="w-20">Sigla</th>
                  <th className="w-96">Nombre</th>
                  <th className="w-8">Crd</th>
                  <th className="w-48">Unidad Academica</th>
                  <th className="w-8"></th>
                </tr>
              </thead>
              <tbody onScroll={handleScroll} className="bg-white flex flex-col items-center justify-between overflow-y-scroll w-full max-h-72 pt-2">
              {courses.map((course: Course) => (
                <tr key={course.code} className="flex w-full mb-3">
                  <td className="w-8">
                    <input className='ml-1' id={course.code} type="radio" name="status" value={course.code} onChange={e => setSelectedCourse(e.target.value)}/>
                  </td>
                  <td className='w-20'>{course.code}</td>
                  <td className='w-96'>{course.name}</td>
                  <td className='w-8'>{course.credits}</td>
                  <td className='w-48'>{course.school}</td>
                  <th className="w-8"></th>
                </tr>
              ))}</tbody>
            </table>
            <div className='right-0'>{courses.length} - {equivalence.courses.length}</div>
            <div className='float-right mx-3 '>
              <button className="btn mr-2" onClick={() => onClose()}>Cancelar</button>
              <button className="btn " onClick={() => onClose(selectedCourse)}>Guardar</button>
            </div>
          </Dialog.Panel>
        </div>
      </div>
    </Dialog>
  )
}

export default CourseSelectorDialog
