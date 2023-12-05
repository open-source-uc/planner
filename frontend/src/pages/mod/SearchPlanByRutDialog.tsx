import { memo, useState } from 'react'
import TextInputModal from '../../components/TextInputModal'

const SearchPlanByRutModal = ({ isOpen, status, error, studentInitialSearch, onClose, searchUser }: { isOpen: boolean, status: 'error' | 'success' | 'loading', error: unknown, studentInitialSearch: string, onClose: Function, searchUser: Function }): JSX.Element => {
  const [studentRut, setStudentRut] = useState<string>(studentInitialSearch)
  const isSaveButtonDisabled: boolean = studentRut.length < 2

  const handleInputChange: React.EventHandler<React.ChangeEvent<HTMLInputElement>> = e => {
    const input = e.target.value
    let cleanedInput = input.replace(/[^0-9kK]/g, '')
    if (cleanedInput.length > 7) cleanedInput = cleanedInput.slice(0, -1) + '-' + cleanedInput.slice(-1)
    if (cleanedInput.length < 11 && (e.target.value === '' || cleanedInput !== '')) setStudentRut(cleanedInput)
  }

  return (
    <TextInputModal
      title="Rut del estudiante"
      isOpen={isOpen}
      handleAccept={searchUser}
      handleInputChange={handleInputChange}
      onClose={onClose}
      acceptMessage="Buscar"
      error={status === 'error'}
      errorMsg="Estudiante no encontrado."
      isLoading={status === 'loading'}
      inputValue={studentRut}
      isAcceptButtonDisabled={isSaveButtonDisabled}
    />
  )
}

export default memo(SearchPlanByRutModal)
