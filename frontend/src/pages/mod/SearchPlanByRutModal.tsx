import { memo, useRef, useState, Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { DefaultService } from '../../client'
import { isApiError } from '../planner/utils/Types'
const SearchPlanByRutModal = ({ isOpen, onClose, searchPlans }: { isOpen: boolean, onClose: Function, searchPlans: Function }): JSX.Element => {
  const planNameInput = useRef(null)
  const acceptButton = useRef<HTMLButtonElement>(null)
  const [studentRut, setStudentRut] = useState<string>('')
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [isUserNotFound, setIsUserNotFound] = useState<boolean>(false)
  const isSaveButtonDisabled: boolean = studentRut === ''

  const handleUserSearch = async (rut: string): Promise<void> => {
    setIsUserNotFound(false)
    setIsLoading(true)
    let formattedRut = rut
    if (formattedRut.charAt(formattedRut.length - 2) !== '-') {
      formattedRut = formattedRut.slice(0, -1) + '-' + formattedRut.slice(-1)
    }
    try {
      const stundetInfo = await DefaultService.getStudentInfoForAnyUser(formattedRut)
      searchPlans(stundetInfo, studentRut)
      setIsUserNotFound(false)
      onClose()
    } catch (err) {
      if (isApiError(err) && (err.status === 404 || err.status === 403)) {
        setIsUserNotFound(true)
      }
      console.log(err)
    }
    setIsLoading(false)
  }

  const handleKeyDown: React.EventHandler<React.KeyboardEvent<HTMLInputElement>> = e => {
    if (e.key === 'Enter') {
      e.preventDefault()
      if (isSaveButtonDisabled) return
      try {
        void handleUserSearch(studentRut)
      } catch (err) {
        console.log(err)
      }
    }
  }

  const handleInputChange: React.EventHandler<React.ChangeEvent<HTMLInputElement>> = e => {
    const input = e.target.value
    let cleanedInput = input.replace(/[^0-9kK]/g, '')
    if (cleanedInput.length > 7) cleanedInput = cleanedInput.slice(0, -1) + '-' + cleanedInput.slice(-1)
    if (cleanedInput.length < 11 && (e.target.value === '' || cleanedInput !== '')) setStudentRut(cleanedInput)
  }

  const handleClick = (): void => {
    void handleUserSearch(studentRut)
  }

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
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:max-w-lg">
                <div className="bg-white pb-4 pt-5 sm:p-6 sm:pb-4">
                  <div className="sm:flex sm:items-start p-3">
                    <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                      <Dialog.Title as="h3" className="text-lg font-semibold leading-6 text-gray-900">
                         Rut del estudiante:
                      </Dialog.Title>
                      <div className="mt-2">
                        <input className={`grow rounded py-1 w-full my-2 sentry-mask ${isUserNotFound ? 'border-red-500' : ''}`} type="text" id="planName" value={studentRut} onChange={handleInputChange} onKeyDown={handleKeyDown}/>
                      </div>

                      {isUserNotFound && (
                        <div className="text-red-500 text-sm">Estudiante no encontrado.</div>
                      )}
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
                {isLoading
                  ? <div className="w-full text-center text-sm py-2 px-4">Buscando...</div>
                  : <>
                      <button
                    type="button"
                    ref={acceptButton}
                    disabled={isSaveButtonDisabled}
                    className='inline-flex w-full justify-center rounded-md text-sm btn shadow-sm sm:ml-3 sm:w-auto disabled:bg-gray-400'
                    onClick={handleClick}
                  >
                    Buscar
                  </button>
                  <button
                    type="button"
                    className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 sm:w-auto"
                    onClick={() => onClose()}
                  >
                    Cancelar
                  </button>
                  </>}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}

export default memo(SearchPlanByRutModal)
