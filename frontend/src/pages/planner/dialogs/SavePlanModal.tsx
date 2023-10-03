import { memo, useState } from 'react'
import TextInputModal from '../../../components/TextInputModal'

const SavePlanModal = ({ isOpen, onClose, savePlan }: { isOpen: boolean, onClose: Function, savePlan: Function }): JSX.Element => {
  const [planName, setPlanName] = useState<string>('')

  const isSaveButtonDisabled: boolean = planName === ''

  return (
    <TextInputModal
      title="Nombre de la planificación"
      isOpen={isOpen}
      handleAccept={savePlan}
      onClose={onClose}
      acceptMessage="Guardar"
      error={false}
      errorMsg="Nombre invalido."
      isLoading={false}
      isAcceptButtonDisabled={isSaveButtonDisabled}
      inputValue={planName}
      handleInputChange={(e: React.ChangeEvent<HTMLInputElement>) => { setPlanName(e.target.value) }}
    />
  )
}

export default memo(SavePlanModal)
