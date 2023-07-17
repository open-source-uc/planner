
import { useEffect } from 'react'
import { DefaultService, type ConcreteId } from '../../../client'

const DebugGraph = ({ getDefaultPlan }: { getDefaultPlan: Function }): JSX.Element => {
  // https://stackoverflow.com/questions/61740073/how-to-detect-keydown-anywhere-on-page-in-a-react-app
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
      const basePlan = await DefaultService.emptyGuestPlan()
      basePlan.classes = newClasses
      await getDefaultPlan(basePlan)
    }

    window.addEventListener('paste', e => { void handlePaste(e) })

    // Don't forget to clean up
    return () => {
      window.removeEventListener('paste', e => { void handlePaste(e) })
    }
  }, [])

  return (
    <></>
  )
}

export default DebugGraph
