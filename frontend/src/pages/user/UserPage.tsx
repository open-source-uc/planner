// import UserInfo from '../components/UserInfo'
import CurriculumList from './CurriculumList'

/**
 * The user page. Contains the list of curriculums and some user information.
 */
const UserPage = (): JSX.Element => {
  return (

  <div className="flex my-2 h-full">
    <div className="mx-auto"> <CurriculumList /></div>
    {/* <div className="w-1/3 bg-blue-100"><UserInfo /></div> */}
  </div>

  )
}

export default UserPage
