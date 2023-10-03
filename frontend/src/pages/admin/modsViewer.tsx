import AddModByRutModal from './addMod'
import { toast } from 'react-toastify'
import { useState } from 'react'
import { DefaultService, type AccessLevelOverview } from '../../client'
import { Spinner } from '../../components/Spinner'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { useAuth } from '../../contexts/auth.context'
import { isApiError } from '../planner/utils/Types'

async function addMod (rut: string): Promise<AccessLevelOverview> {
  if (rut === '') return await Promise.resolve({})
  return await DefaultService.addMod(rut)
}

async function removeMod (rut: string): Promise<string> {
  try {
    await DefaultService.removeMod(rut)
    console.log('moderador removido')
    toast.success('Permisos de moderador removido exitosamente')
    return rut
  } catch (err) {
    console.log(err)
    if (isApiError(err) && err.status === 401) {
      console.log('token invalid or expired, loading re-login page')
      toast.error('Token invalido. Redireccionando a pagina de inicio...')
    }
    return ''
  }
}

function getDateString (date: string): string {
  const mydate = date.split('T')[0].split('-').reverse().join('-')
  return mydate
}

const ModsViewer = (): JSX.Element => {
  const authState = useAuth()
  const [searchingPlanModalIsOpen, setSearchingPlanModalIsOpen] = useState<boolean>(authState?.student?.rut === null)

  const queryClient = useQueryClient()

  const { status, error, data } = useQuery({
    queryKey: ['mods'],
    queryFn: async () => await DefaultService.viewMods()
  })

  const addModMutation = useMutation(addMod, {
    onSuccess: (newMod) => {
      queryClient.setQueryData(['mods'], (old) =>
        [...old, newMod]
      )
      setSearchingPlanModalIsOpen(false)
    }
  })

  const removeModMutation = useMutation(removeMod, {
    onSuccess: (removedModRut) => {
      queryClient.setQueryData(['mods'], (old) =>
        old.filter((e) => e.user_rut !== removedModRut)
      )
      setSearchingPlanModalIsOpen(false)
    }
  })

  return (
    <div>
      <AddModByRutModal
          isOpen = {searchingPlanModalIsOpen}
          onClose = {() => { setSearchingPlanModalIsOpen(false) }}
          addMod = {addModMutation.mutateAsync}
      />
      <div className="flex my-2 h-full">
        <div className="mx-auto">
          <div className="flex mb-4 h-full w-full">
            <div className="m-3 w-full">
              <div className="flex gap-4 items-center">
                  <h2 className="text-3xl font-medium leading-normal mb-2 text-gray-800 text-center">Usuarios moderadores:</h2>
                  <button className="btn" onClick={() => {
                    setSearchingPlanModalIsOpen(true)
                  }}>Agregar Moderador</button>
              </div>
              {status === 'loading' && <div className="mt-5"><Spinner message="Cargando moderadores..." /></div>}

              {status === 'error' && <div className="mx-auto my-auto"><p className="text-gray-500 text-center">{isApiError(error) && error.message}</p></div>}

              {status === 'success' && data.length === 0 && <div className="mx-auto my-auto"><p className="text-gray-500 text-center">No existe ningun moderador, por favor anada uno con el buscador.</p></div>}

              {(status === 'success' && data.length > 0 &&
              <div className='relative overflow-x-auto shadow-md sm:rounded-lg max-w-2xl mt-2'>
                  <table className="w-full text-sm text-left text-gray-500">
                    <thead className="text-xs text-gray-700 uppercase bg-gray-50 ">
                      <tr className="border-b-4 border-gray-600">
                          <th scope="col" className="px-6 py-3">Rut</th>
                          <th scope="col" className="px-6 py-3">Fecha Creación</th>
                          <th scope="col" className="px-6 py-3">Fecha Modificación</th>
                          <th scope="col" className="px-6 py-3"><span className="sr-only">Acciones</span></th>
                      </tr>
                    </thead>
                    <tbody className='bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600'>
                      {data?.map((mod: AccessLevelOverview) => {
                        return (
                          <tr key={mod.user_rut} className='bg-white border-b  hover:bg-gray-50 '>
                            <th scope="row" className="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">
                              {mod.user_rut}
                            </th>
                            <td className='px-6 py-4'>{getDateString(mod.created_at)}</td>
                            <td className='px-6 py-4'>{getDateString(mod.updated_at)}</td>
                            <td className='px-6 py-4 text-right'><div className='space-x-4 items-center'>
                              <button className='text-red-600'
                                  onClick={() => {
                                    void removeModMutation.mutateAsync(
                                      mod.user_rut
                                    )
                                  }}>Remover</button>
                            </div></td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>)}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ModsViewer
