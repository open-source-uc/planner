import { Fragment, memo } from 'react'
import { Dialog, Transition, Tab } from '@headlessui/react'

const LegendModal = ({ open, onClose }: { open: boolean, onClose: Function }): JSX.Element => {
  return (
    <Transition.Root show={open} as={Fragment}>
    <Dialog as="div" className="modal relative" onClose={() => { onClose() }}>
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
                  Leyenda e Instrucciones
                </Dialog.Title>

                <div className="w-full p-2">
                  <Tab.Group>
                    <Tab.List className="flex space-x-1 rounded-xl bg-blue-900/20 p-1">
                      <Tab as={Fragment}>
                        {({ selected }) => (
                          <button
                            className={
                              `w-full rounded-lg py-2.5 text-sm font-medium leading-5 text-blue-700 ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2',
                              ${selected
                                ? 'bg-white shadow'
                                : 'text-blue-100 hover:bg-white/[0.12] hover:text-white'}`
                            }
                          >
                            Importante
                          </button>
                        )}
                      </Tab>
                      <Tab as={Fragment}>
                        {({ selected }) => (
                          <button
                          className={
                            `w-full rounded-lg py-2.5 text-sm font-medium leading-5 text-blue-700 ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2',
                            ${selected
                              ? 'bg-white shadow'
                              : 'text-blue-100 hover:bg-white/[0.12] hover:text-white'}`
                          }
                        >
                          Leyenda
                        </button>
                        )}
                      </Tab>
                      <Tab as={Fragment}>
                        {({ selected }) => (
                          <button
                          className={
                            `w-full rounded-lg py-2.5 text-sm font-medium leading-5 text-blue-700 ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2',
                            ${selected
                              ? 'bg-white shadow'
                              : 'text-blue-100 hover:bg-white/[0.12] hover:text-white'}`
                          }
                        >
                          Instrucciones
                        </button>
                        )}
                      </Tab>
                    </Tab.List>
                    <Tab.Panels className="mt-2">
                      <Tab.Panel className='rounded-xl bg-white p-3 ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2'>
                        <p className="text-sm text-gray-500">Esta malla curricular es la recomendada y está sujeta a modificaciones conforme a la planificación académica vigente al momento de inscribir cursos.</p>
                        <p className="text-sm text-gray-500 my-1">Los requisitos y planificación de los cursos pueden ir variando semestre a semestre. Por lo que PanguiPath puede tener algunas variaciones. La información oficial de los requisitos y planificación de los cursos se encuentra disponible en el catálogo de cursos (http://catalogo.uc.cl/) y el libro de cursos (http://buscacursos.uc.cl/).</p>
                        <p className="text-sm text-gray-500">Es responsabilidad del alumno verificar que el avance curricular determinado por PanguiPath sea el correcto. Los Planes de Estudios publicados en Siding corresponden a la información oficial y actualizada.</p>
                      </Tab.Panel>
                      <Tab.Panel className='rounded-xl bg-white p-3 ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2'>Content 2</Tab.Panel>
                      <Tab.Panel className='rounded-xl bg-white p-3 ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2'>Content 3</Tab.Panel>
                    </Tab.Panels>
                  </Tab.Group>
                </div>
                <div className="mt-4">
                  <button
                    type="button"
                    className="inline-flex justify-center rounded-md border border-transparent bg-blue-100 px-4 py-2 text-sm font-medium text-blue-900 hover:bg-blue-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                    onClick={() => onClose()}
                  >
                    Got it, thanks!
                  </button>
                </div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </div>
    </Dialog>
    </Transition.Root>
  )
}

export default memo(LegendModal)
