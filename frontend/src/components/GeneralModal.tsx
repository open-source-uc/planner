
import { memo, Fragment, type MutableRefObject, type ReactNode } from 'react'
import { Dialog, Transition } from '@headlessui/react'

interface GeneralModalProps {
  isOpen: boolean
  onClose: Function
  initialFocus?: MutableRefObject<any>
  children?: ReactNode
}

const GeneralModal: React.FC<GeneralModalProps> = ({ isOpen, onClose, initialFocus, children }) => {
  return (
      <Transition.Root show={isOpen} as={Fragment}>
        <Dialog as="div" className="modal relative" initialFocus={initialFocus} onClose={() => onClose()}>
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
                {children}
              </Transition.Child>
            </div>
          </div>
        </Dialog>
      </Transition.Root>
  )
}
export default memo(GeneralModal)
