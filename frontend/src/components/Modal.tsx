import { useState, useRef, useEffect } from 'react'
import { Dialog } from '@headlessui/react'
import { DefaultService, Equivalence, Course } from '../client'
import info from '../assets/info.svg'

const MyDialog = ({ equivalence, open, onClose }: { equivalence?: Equivalence, open: boolean, onClose: Function }): JSX.Element => {
  const [courses, setCourses] = useState<Course[]>([])
  const [selectedCourse, setSelectedCourse] = useState('')

  const previousClasses = useRef('')
  async function getCourseDetails (equivalence: Equivalence): Promise<void> {
    const response = await DefaultService.getCourseDetails(equivalence.courses)
    setCourses(response)
    previousClasses.current = equivalence.code
  }

  useEffect(() => {
    if (!open)setCourses([])
    else if (equivalence !== undefined) getCourseDetails(equivalence).catch(err => console.log(err))
  }, [open])
  console.log(courses)
  if (equivalence === undefined) return <></>
  return (
    <Dialog as="div" className="relative z-10" open={open} onClose={() => onClose()}>
        <div className="fixed inset-0 overflow-y-auto">
            <div className="flex items-center min-h-screen justify-center p-4 text-center">
                <Dialog.Panel className="w-full overflow-y-hidden max-w-4xl transform  rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                    <Dialog.Title as="h3" className="text-lg font-medium leading-6 text-gray-900">
                        {equivalence.name}
                    </Dialog.Title>
                    <table className="text-left table-auto w-11/12 p-3 m-auto">
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
                        <tbody className="bg-grey-light flex flex-col items-center justify-between overflow-y-scroll w-full max-h-96">
                        {courses.map((course: Course) => (
                            <tr key={course.code} className="flex w-full mb-3">
                                <td className="w-8"><input className='ml-1' id={course.code} type="radio" name="status" value={course.code} onChange={e => setSelectedCourse(e.target.value)}/></td>
                                <td className='w-20'>{course.code}</td>
                                <td className='w-96'>{course.name}</td>
                                <td className='w-8'>{course.credits}</td>
                                <td className='w-48'>{course.school}</td>
                                <th className="w-8"><img height="15" src={info} alt="Info del Curso" /></th>
                            </tr>
                        ))}</tbody>
                    </table>

                    <button onClick={() => onClose()}>Cancelar</button>
                    <button onClick={() => onClose(selectedCourse)}>Guardar</button>
                </Dialog.Panel>
                </div>
                </div>
    </Dialog>
  )
}

export default MyDialog
