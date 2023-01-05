// import { useAuth } from '../contexts/auth.context'
import UserInfo from '../components/UserInfo'
import CurriculumList from '../components/CurriculumList'

/**
 * The user page. Contains the list of curriculums and some puser information.
 */
const UserPage = (): JSX.Element => {
  // const authState = useAuth()
  // const [loading, setLoading] = useState(false)

  return (

  <div className="flex mb-4 h-full">
    <div className="w-2/3 bg-gray-500"> <CurriculumList /></div>
    <div className="w-1/3 bg-teal-100"><UserInfo /></div>
  </div>

  )
}

export default UserPage
