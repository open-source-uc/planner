import { Fragment, useState, useEffect, useRef, memo, type ReactNode } from 'react'
import { Dialog, Transition } from '@headlessui/react'

interface AlertModalProps {
  title: string | ReactNode
  isOpen: boolean
  close: Function
  disclaimer?: boolean
  children?: ReactNode
}

function useCanClose ({ disclaimer, close }: { close: Function, disclaimer?: boolean }): [boolean, (aceptIt: boolean) => void, React.RefObject<HTMLButtonElement>] {
  const cancelButtonRef = useRef<HTMLButtonElement>(null)
  const [canClose, setCanClose] = useState(false)

  useEffect(() => {
    console.log(localStorage.getItem('reconexion'))
    if (disclaimer === true && localStorage.getItem('reconexion') === null) {
      const timer = setTimeout(() => {
        setCanClose(true)
        localStorage.setItem('reconexion', 'true')
      }, 5000)

      return () => {
        clearTimeout(timer)
      }
    } else {
      setCanClose(true)
    }
  }, [disclaimer])

  const handleClose = (aceptIt: boolean): void => {
    if (canClose || disclaimer !== true) {
      close(aceptIt)
    }
  }

  return [canClose, handleClose, cancelButtonRef]
}

const AlertModal: React.FC<AlertModalProps> = ({ title, isOpen, close, disclaimer, children }: AlertModalProps) => {
  const [canClose, handleClose, cancelButtonRef] = useCanClose({ disclaimer, close })

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="modal relative" initialFocus={cancelButtonRef} onClose={() => { console.log('alert closed') }}>
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
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-xl">
                <div className="bg-white px-4 pb-4 pt-6 sm:p-6 sm:pb-4">
                  <div className="sm:flex sm:items-start">
                    <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                      <Dialog.Title as="h3" className="text-2xl font-semibold leading-6 text-gray-900">
                        {title}
                      </Dialog.Title>
                      <div className="mt-4">
                        { (typeof children === 'string')
                          ? <p className="text-sm text-gray-700">
                        {children}
                        </p>
                          : children }
                      </div>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
                  <button
                    type="button"
                    disabled={!canClose}
                    className="disabled:opacity-50 disabled:cursor-not-allowed inline-flex w-full justify-center rounded-md text-sm btn shadow-sm sm:ml-3 sm:w-auto"
                    onClick={() => { handleClose(false) }}
                  >
                    Continuar
                  </button>
                  {disclaimer !== true && <button
                    type="button"
                    className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 sm:w-auto"
                    onClick={() => { handleClose(true) }}
                    ref={cancelButtonRef}
                  >
                    Cancelar
                  </button>}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}

export default memo(AlertModal)
