
import { DefaultService, type ValidatablePlan } from '../client'
import { useEffect } from 'react'

const DebugGraph = ({ validatablePlan }: { validatablePlan: ValidatablePlan | null }): JSX.Element => {
  // https://stackoverflow.com/questions/61740073/how-to-detect-keydown-anywhere-on-page-in-a-react-app
  useEffect(() => {
    const showGraph = async (mode: string): Promise<void> => {
      if (validatablePlan === null) return
      const g = await DefaultService.getCurriculumValidationGraph(mode, validatablePlan)
      window.open(`https://dreampuf.github.io/GraphvizOnline/#${encodeURI(g)}`)
    }

    const handleWrapper = (e: KeyboardEvent): void => {
      let mode = null
      switch (e.key) {
        case 'F1': mode = 'pretty'; break
        case 'F2': mode = 'debug'; break
        case 'F3': mode = 'raw'; break
      }
      if (mode != null) {
        e.preventDefault()
        showGraph(mode).then(() => {
          console.log('curriculum graph opened in pop-up window')
        }).catch(e => { console.error(e) })
      }
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
