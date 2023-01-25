export function Spinner (): JSX.Element {
  return <div className='mx-auto my-auto w-20 h-10'>
            <div className="flex justify-center items-center mb-4">
              <div className="spinner-border animate-spin inline-block w-8 h-8 border-4 rounded-full" role="status">
              </div>
            </div>
            <p>Cargando...</p>
          </div>
}
