import { memo, useRef, useState, Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'

const SavePlanModal = ({ isOpen, onClose, savePlan }: { isOpen: boolean, onClose: Function, savePlan: Function }): JSX.Element => {
  const planNameInput = useRef(null)
  const [planName, setPlanName] = useState<string>('')

  const isSaveButtonDisabled: boolean = planName === ''

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="modal relative" initialFocus={planNameInput} onClose={() => onClose() }>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg">
                <div className="bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
                  <div className="sm:flex sm:items-start">
                    <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                      <Dialog.Title as="h3" className="text-lg font-semibold leading-6 text-gray-900">
                         ¿Cómo quieres llamarle a esta planificación?
                      </Dialog.Title>
                      <div className="mt-2">
                        <label className="mr-3 my-auto" htmlFor="planName">Nombre de la planificación: </label>
                        <input className="grow rounded py-1" type="text" id="planName" value={planName} onChange={(e) => { setPlanName(e.target.value) }}/>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
                  <button
                    type="button"
                    disabled={isSaveButtonDisabled}
                    className='inline-flex w-full justify-center rounded-md text-sm btn shadow-sm sm:ml-3 sm:w-auto disabled:bg-gray-400'
                    onClick={() => {
                      savePlan(planName)
                      onClose()
                    }}
                  >
                    Guardar
                  </button>
                  <button
                    type="button"
                    className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 sm:w-auto"
                    onClick={() => onClose()}
                  >
                    Cancelar
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

export default memo(SavePlanModal)
