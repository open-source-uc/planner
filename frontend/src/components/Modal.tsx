import { useState } from 'react'
import { Dialog } from '@headlessui/react'
import { Equivalence } from '../client'

const MyDialog = ({ equivalence, open, onClose }: { equivalence?: Equivalence, open: boolean, onClose: Function }): JSX.Element => {
  const [selectedCourse, setSelectedCourse] = useState('')
  if (equivalence === undefined) return <div />
  return (
    <Dialog as="div" className="relative z-10" open={open} onClose={() => onClose()}>
        <div className="fixed inset-0 overflow-y-auto">
            <div className="flex items-center min-h-screen justify-center p-4 text-center">
                <Dialog.Panel className="w-full max-w-4xl transform  rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                    <Dialog.Title as="h3" className="text-lg font-medium leading-6 text-gray-900">
                        {equivalence.name}
                    </Dialog.Title>
                    <div className='ml-10 '>Sigla</div>
                    <div className='max-h-96 overflow-y-auto'>
                    {equivalence.courses.map((code: string) => (
                        <div key={code}>
                            <input className='ml-1' id={code} type="radio" name="status" value={code} onChange={e => setSelectedCourse(e.target.value)}/>
                            <label className='ml-3'>{code}</label>
                        </div>
                    ))}</div>

                    <button onClick={() => onClose()}>Cancelar</button>
                    <button onClick={() => onClose(selectedCourse)}>Guardar</button>
                </Dialog.Panel>
                </div>
                </div>
    </Dialog>
  )
}

export default MyDialog
