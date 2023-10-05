import { useState } from 'react'

interface ModalState {
  isModalOpen: boolean
  openModal: Function
  closeModal: Function
}

const useDummyModal = (): ModalState => {
  const [isModalOpen, setIsModalOpen] = useState(false)

  const openModal = (): void => {
    setIsModalOpen(true)
  }

  const closeModal = (): void => {
    setIsModalOpen(false)
  }

  return {
    isModalOpen,
    openModal,
    closeModal
  }
}

export default useDummyModal
