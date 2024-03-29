
import { useEffect } from 'react'
import { type ConcreteId, type ValidatablePlan } from '../../../client'

const ReceivePaste = ({ validatablePlan, getDefaultPlan }: { validatablePlan: ValidatablePlan | null, getDefaultPlan: Function }): JSX.Element => {
  useEffect(() => {
    const handlePaste = async (e: ClipboardEvent): Promise<void> => {
      const text = e.clipboardData?.getData('text/plain')
      if (text == null) return
      const courseRegex = /[A-Z]{3}\d{3}[A-Z\d]?/g
      const periodRegex = /\d-\d{4}/g
      const semesters = text.split(periodRegex).slice(1).map(period => [...period.matchAll(courseRegex)].map(match => match[0]))
      if (semesters.length === 0 || semesters.some(sem => sem.length === 0)) return
      console.log('pasting', semesters)
      const newClasses = semesters.map(sem => sem.map((courseCode): ConcreteId => ({ is_concrete: true, code: courseCode })))
      const basePlan = { ...validatablePlan, classes: newClasses }
      await getDefaultPlan(basePlan, newClasses.length)
    }

    const wrapper = (e: ClipboardEvent): void => { void handlePaste(e) }

    window.addEventListener('paste', wrapper)

    // Don't forget to clean up
    return () => {
      window.removeEventListener('paste', wrapper)
    }
  }, [validatablePlan, getDefaultPlan])

  return (
    <></>
  )
}

export default ReceivePaste
