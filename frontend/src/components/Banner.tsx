
interface BannerProps {
  bannerType: 'Warning' | 'Error'
  text: string
}

const Banner = ({ bannerType, text }: BannerProps): JSX.Element => {
  return (
        <div className={`flex py-2 px-4  border 
        ${bannerType === 'Warning' ? 'text-yellow-700 border-yellow-300 bg-yellow-50' : ''}
        ${bannerType === 'Error' ? 'text-red-800 border-red-300 bg-red-50' : ''}
        font-semibold`}>
          <p>
            <svg aria-hidden="true" className="mr-2 flex-shrink-0 inline-flex w-5 h-5 m-auto align-text-bottom" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"></path></svg>
            {text}</p>
        </div>
  )
}

export default Banner
