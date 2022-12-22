import ErrorTray from './ErrorTray'
import PlanBoard from './PlanBoard'
import { useState, useEffect } from 'react'
import { DefaultService, Diagnostic } from '../../client'

/**
 * The main planner app. Contains the drag-n-drop main PlanBoard, the error tray and whatnot.
 */
const Planner = (): JSX.Element => {
  const [plan, setPlan] = useState<string[][]>([['MAT1610', 'QIM100A', 'MAT1203', 'ING1004', 'FIL2001'],
    ['MAT1620', 'FIS1513', 'FIS0151', 'ICS1513', 'IIC1103'],
    ['MAT1630', 'FIS1523', 'FIS0152', 'MAT1640'],
    ['EYP1113', 'FIS1533', 'FIS0153', 'IIC2233'],
    ['IIC2143', 'ING2030', 'IIC1253'],
    ['IIC2113', 'IIC2173', 'IIC2413'],
    ['IIC2133', 'IIC2513', 'IIC2713'],
    ['IIC2154']])
  const [validationDiagnostics, setValidationDiagnostics] = useState<Diagnostic[]>([])
  useEffect(() => {
    console.log(plan)
  }, [plan])
  useEffect(() => {
    /* const getBasicPlan = async (): Promise<void> => {
      console.log('getting Basic Plan...')
      const response = await DefaultService.generatePlan({
        classes: [[]],
        next_semester: 0
      })
      setValidationDiagnostics(response.diagnostics)
      console.log('plan generated')
    }
    getBasicPlan().catch(err => {
      console.log(err)
    }) */
    const validate = async (): Promise<void> => {
      console.log('validating...')
      const response = await DefaultService.validatePlan({
        classes: plan,
        next_semester: 1
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
      <PlanBoard />
      <ErrorTray diagnostics={validationDiagnostics} />
    </div>
  )
}

export default Planner
