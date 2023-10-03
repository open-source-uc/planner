import { useRef, type ReactNode, type ChangeEventHandler } from 'react'
import type React from 'react'
import { memo } from 'react'
import { Dialog } from '@headlessui/react'
import GeneralModal from './GeneralModal'

interface TextInputModalProps {
  title: string | ReactNode
  isOpen: boolean
  handleAccept: Function
  onClose: Function
  acceptMessage: string
  error: boolean
  errorMsg: string
  isLoading: boolean
  isAcceptButtonDisabled: boolean
  inputValue: string
  handleInputChange: ChangeEventHandler<HTMLInputElement>
}

const TextInputModal: React.FC<TextInputModalProps> = ({ title, isOpen, handleAccept, onClose, acceptMessage, error, isLoading, isAcceptButtonDisabled, errorMsg, inputValue, handleInputChange }: TextInputModalProps) => {
  const searchText = useRef<HTMLInputElement>(null)

  const handleKeyDown: React.EventHandler<React.KeyboardEvent<HTMLInputElement>> = e => {
    if (e.key === 'Enter') {
      e.preventDefault()
      if (isAcceptButtonDisabled) return
      try {
        void handleAccept(inputValue)
      } catch (err) {
        console.log(err)
      }
    }
  }

  const handleClick = (): void => {
    void handleAccept(inputValue)
  }

  return (
    <GeneralModal isOpen={isOpen} onClose={close} initialFocus={searchText}>
        <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:max-w-lg">
            <div className="bg-white pb-4 pt-5 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start p-3">
                <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                    <Dialog.Title as="h3" className="text-lg font-semibold leading-6 text-gray-900">
                        {title}:
                    </Dialog.Title>
                    <div className="mt-2">
                    <input className={`grow rounded py-1 w-full my-2 sentry-mask ${error ? 'border-red-500' : ''}`} type="text" id="planName" value={inputValue} ref={searchText} onChange={handleInputChange} onKeyDown={handleKeyDown}/>
                    </div>

                    {error && (
                    <div className="text-red-500 text-sm">{errorMsg}</div>
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
                disabled={isAcceptButtonDisabled}
                className='inline-flex w-full justify-center rounded-md text-sm btn shadow-sm sm:ml-3 sm:w-auto disabled:bg-gray-400'
                onClick={handleClick}
                >
                {acceptMessage}
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
    </GeneralModal>
  )
}

export default memo(TextInputModal)
