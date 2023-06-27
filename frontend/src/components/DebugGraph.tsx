
import { DefaultService, type ValidatablePlan } from '../client'
import { useEffect } from 'react'

const DebugGraph = ({ validatablePlan }: { validatablePlan: ValidatablePlan | null }): JSX.Element => {
  // https://stackoverflow.com/questions/61740073/how-to-detect-keydown-anywhere-on-page-in-a-react-app
  useEffect(() => {
    const handleKeyDown = async (e: KeyboardEvent): Promise<boolean> => {
      if (e.key === 'F1') {
        if (validatablePlan === null) return false
        const g = await DefaultService.getCurriculumValidationGraph(validatablePlan)
        window.open(`https://dreampuf.github.io/GraphvizOnline/#${encodeURI(g)}`)
        return true
      }
      return false
    }

    const handleWrapper = (e: KeyboardEvent): void => {
      handleKeyDown(e).then((opened) => {
        if (opened) {
          console.log('curriculum graph opened in pop-up window')
        }
      }).catch(e => { console.error(e) })
    }

    document.addEventListener('keydown', handleWrapper)

    // Don't forget to clean up
    return () => {
      document.removeEventListener('keydown', handleWrapper)
    }
  }, [validatablePlan])

  return (
    <></>
  )
}

export default DebugGraph
