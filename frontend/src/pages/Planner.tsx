import ErrorTray from './ErrorTray'
import PlannerStudio from './PlannerStudio'
import { useState, useEffect } from 'react'
import { DefaultService } from '../client'

const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<string[][]>([])
  const [validationMessages, setValidationMessages] = useState<string[]>([])

  useEffect(() => {
    const validate = async (): Promise<void> => {
      console.log('validating...')
      const response = await DefaultService.validatePlan({
        classes: plan,
        next_semester: 1
      })
      const messages = []
      for (const [code, err] of Object.entries(response.diagnostic)) {
        messages.push(`${code}: ${err}!`)
      }
      setValidationMessages(messages)
      console.log('validated')
    }
    validate().catch(err => {
      setValidationMessages([err.toString()])
    })
  }, [plan])

  return (
    <div className="w-full h-full overflow-hidden flex flex-row justify-items-stretch border-red-400 border-2">
      <PlannerStudio plan={plan} onPlanChange={setPlan} />
      <ErrorTray messages={validationMessages} />
    </div>
  )
}

export default Planner
