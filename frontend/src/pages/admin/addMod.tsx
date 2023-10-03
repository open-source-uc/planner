import { memo, useState } from 'react'
import TextInputModal from '../../components/TextInputModal'
import { isApiError } from '../planner/utils/Types'

const AddModByRutModal = ({ isOpen, onClose, addMod }: { isOpen: boolean, onClose: Function, addMod: Function }): JSX.Element => {
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [isRutInvalid, setIsRutInvalid] = useState<boolean>(false)
  const [modRut, setModRut] = useState<string>('')

  const handleInputChange: React.EventHandler<React.ChangeEvent<HTMLInputElement>> = e => {
    const input = e.target.value
    let cleanedInput = input.replace(/[^0-9kK]/g, '')
    if (cleanedInput.length > 7) cleanedInput = cleanedInput.slice(0, -1) + '-' + cleanedInput.slice(-1)
    if (cleanedInput.length < 11 && (e.target.value === '' || cleanedInput !== '')) setModRut(cleanedInput)
  }

  const giveModPermit = async (rut: string): Promise<void> => {
    setIsRutInvalid(false)
    setIsLoading(true)
    let formattedRut = rut
    if (formattedRut.charAt(formattedRut.length - 2) !== '-') {
      formattedRut = formattedRut.slice(0, -1) + '-' + formattedRut.slice(-1)
    }
    try {
      await addMod(formattedRut)
      setIsRutInvalid(false)
      onClose()
    } catch (err) {
      if (isApiError(err)) {
        if (err.status === 400) {
          console.log(err.message)
          setIsRutInvalid(true)
        }
      }
    }
    setIsLoading(false)
  }
  return (
    <TextInputModal
      title="Rut del usuario a agregar"
      isOpen={isOpen}
      handleAccept={giveModPermit}
      onClose={onClose}
      acceptMessage="Dar permisos"
      error={isRutInvalid}
      errorMsg="Rut invalido."
      isLoading={isLoading}
      inputValue={modRut}
      isAcceptButtonDisabled={false}
      handleInputChange={handleInputChange}
    />
  )
}

export default memo(AddModByRutModal)
