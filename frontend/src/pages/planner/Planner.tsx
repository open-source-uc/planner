import ErrorTray from './ErrorTray'
import PlanBoard from './PlanBoard'
import { useState, useEffect } from 'react'
import { DefaultService, Diagnostic } from '../../client'

/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */
const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<string[][]>([['MAT1610'], ['MAT1620'], ['MAT1630'], ['IEE1513'], ['IIC2233'], []])
  const [validationDiagnostics, setValidationDiagnostics] = useState<Diagnostic[]>([])

  useEffect(() => {
    const validate = async (): Promise<void> => {
      console.log('validating...')
      const response = await DefaultService.validatePlan({
        plan: {
          classes: plan,
          next_semester: 1
        },
        curriculum: {
          blocks: [
            {
              name: 'Formacion General',
              children: [
                {
                  name: 'OFG',
                  cap: 50,
                  children: [
                    {
                      name: 'Deportivos de 5 creditos',
                      cap: 10,
                      children: ['!dpt5']
                    },
                    'LET0003',
                    {
                      name: 'Teologico',
                      cap: 10,
                      children: ['!ttf']
                    },
                    'FIL188'
                  ]
                }
              ]
            }
          ]
        }
      })
      setValidationDiagnostics(response.diagnostics)
      console.log('validated')
    }
    validate().catch(err => {
      setValidationDiagnostics([{
        is_warning: false,
        message: `Internal error: ${String(err)}`
      }])
    })
  }, [plan])

  return (
    <div className="w-full h-full overflow-hidden flex flex-row justify-items-stretch border-red-400 border-2">
      <PlanBoard plan={plan} onPlanChange={setPlan} />
      <ErrorTray diagnostics={validationDiagnostics} />
    </div>
  )
}

export default Planner
