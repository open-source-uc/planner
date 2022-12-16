import CurriculumTable from '../components/CurriculumTable'
import dummydata from '../../../data/dummy-curriculumn.json'
import type { Course } from '../lib/types'

const Planner = (): JSX.Element => {
  return (
              <div>
              <h2>Planificador</h2>
              <CurriculumTable courses={dummydata as Course[]}/>
              </div>
  )
}

export default Planner
