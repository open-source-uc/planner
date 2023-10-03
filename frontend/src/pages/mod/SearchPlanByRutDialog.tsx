import { memo, useState } from 'react'
import { DefaultService } from '../../client'
import { isApiError } from '../planner/utils/Types'
import TextInputModal from '../../components/TextInputModal'

const SearchPlanByRutModal = ({ isOpen, onClose, searchPlans }: { isOpen: boolean, onClose: Function, searchPlans: Function }): JSX.Element => {
  const [studentRut, setStudentRut] = useState<string>('')
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [isUserNotFound, setIsUserNotFound] = useState<boolean>(false)
  const isSaveButtonDisabled: boolean = studentRut.length < 2

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
      handleAccept={handleUserSearch}
      handleInputChange={handleInputChange}
      onClose={onClose}
      acceptMessage="Buscar"
      error={isUserNotFound}
      errorMsg="Estudiante no encontrado."
      isLoading={isLoading}
      inputValue={studentRut}
      isAcceptButtonDisabled={isSaveButtonDisabled}
    />
  )
}

export default memo(SearchPlanByRutModal)
