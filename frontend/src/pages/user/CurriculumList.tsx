import CurriculumListRow from './CurriculumListRow'
import { ReactComponent as PlusIcon } from '../../assets/plus.svg'
import { Link } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { DefaultService, type LowDetailPlanView, type ApiError } from '../../client'
import { Spinner } from '../../components/Spinner'
import { toast } from 'react-toastify'
import AlertModal from '../../components/AlertModal'

import SavePlanModal from '../planner/dialogs/SavePlanModal'
import useDummyModal from '../../utils/useDummyModal'

const isApiError = (err: any): err is ApiError => {
  return err.status !== undefined
}

const CurriculumList = (): JSX.Element => {
  const [plans, setPlans] = useState <LowDetailPlanView[]>([])
  const [loading, setLoading] = useState <boolean>(true)
  const [popUpAlert, setPopUpAlert] = useState({ isOpen: false, id: '' })

  const [currentEditedId, setCurrentEditedId] = useState <string>('')
  const [currentEditedName, setCurrentEditedName] = useState <string>('')

  const { isModalOpen: isSavePlanModalOpen, openModal: openSavePlanModal, closeModal: closeSavePlanModal } = useDummyModal()

  function compare (a: LowDetailPlanView, b: LowDetailPlanView): number {
    const timestampA = Date.parse(a.updated_at)
    const timestampB = Date.parse(b.updated_at)
    if (timestampA < timestampB) {
      return -1
    }
    if (timestampA > timestampB) {
      return 1
    }
    return 0
  }

  function arrayMove (arr: any[], oldIndex: number, newIndex: number): void {
    if (newIndex >= arr.length) {
      let k = newIndex - arr.length + 1
      while ((k--) !== 0) {
        arr.push(undefined)
      }
    }
    arr.splice(newIndex, 0, arr.splice(oldIndex, 1)[0])
  };

  const readPlans = async (): Promise<void> => {
    const response = await DefaultService.readPlans()
    response.sort(compare).reverse()
    const index = response.findIndex((plan) => plan.is_favorite)
    if (index !== -1) {
      arrayMove(response, index, 0)
    }
    setPlans(response)
    setLoading(false)
  }

  useEffect(() => {
    readPlans().catch(err => {
      console.log(err)
      if (err.status === 401) {
        console.log('token invalid or expired, loading re-login page')
        toast.error('Tu session a expirado. Redireccionando a pagina de inicio de sesion...', {
          toastId: 'ERROR401'
        })
      }
    })
  })

  async function handleFavourite (id: string, planName: string, fav: boolean): Promise<void> {
    try {
      await DefaultService.updatePlanMetadata(id, undefined, !fav)
      await readPlans()
      console.log('plan updated')
    } catch (err) {
      console.log(err)
      if (isApiError(err) && err.status === 401) {
        console.log('token invalid or expired, loading re-login page')
        toast.error('Token invalido. Redireccionando a pagina de inicio...')
      }
    }
  }

  function openEditModal (id: string, name: string): void {
    openSavePlanModal()
    setCurrentEditedId(id)
    setCurrentEditedName(name)
  }

  async function editPlanName (planName: string): Promise<void> {
    if (planName === null || planName === '') return
    try {
      await DefaultService.updatePlanMetadata(currentEditedId, planName, undefined)
      await readPlans()
      console.log('plan updated')
      toast.success('Malla actualizada exitosamente')
    } catch (err) {
      console.log(err)
      if (isApiError(err) && err.status === 401) {
        console.log('token invalid or expired, loading re-login page')
        toast.error('Token invalido. Redireccionando a pagina de inicio...')
      }
    }
    closeSavePlanModal()
    setCurrentEditedId('')
    setCurrentEditedName('')
  }

  async function handleDelete (id: string): Promise<void> {
    try {
      await DefaultService.deletePlan(id)
      await readPlans()
      console.log('plan deleted')
      toast.success('Malla eliminada exitosamente')
    } catch (err) {
      console.log(err)
      if (isApiError(err) && err.status === 401) {
        console.log('token invalid or expired, loading re-login page')
        toast.error('Token invalido. Redireccionando a pagina de inicio...')
      }
    }
  }

  function handlePopUpAlert (isCanceled: boolean): void {
    if (!isCanceled) {
      void handleDelete(popUpAlert.id)
    }
    setPopUpAlert({ isOpen: false, id: '' })
  }

  return (
      <div className="flex mb-4 h-full w-full">
        <SavePlanModal isOpen={isSavePlanModalOpen} onClose={closeSavePlanModal} savePlan={editPlanName} defaultValue={currentEditedName}/>
        <AlertModal title={'Eliminar malla'} isOpen={popUpAlert.isOpen} close={handlePopUpAlert}>{'¿Estás seguro/a de que deseas eliminar esta malla? Esta accion es irreversible'}</AlertModal>
          <div className="m-3 w-full">
                <div className="flex gap-4 items-center">
                    <h2 className="text-3xl font-medium leading-normal mb-2 text-gray-800 text-center">Mis mallas</h2>
                    <Link to="/planner/new">
                        <div className="hover-text">
                            <button><PlusIcon className="w-8 h-8" title="Crear nueva malla"/></button>
                            <span className="tooltip-text">Crear nueva malla</span>
                        </div>
                    </Link>
                </div>

                { loading && <div className="mt-5"><Spinner message="Cargando planificaciones..." /></div> }

                { !loading && plans.length === 0 && <div className="mx-auto my-auto"><p className="text-gray-500 text-center">Todavía no tienes ninguna malla. Puedes partir <Link to="/planner/new" className='underline'>creando una nueva.</Link></p></div>}

                { !loading && plans.length > 0 && <div className='relative overflow-x-auto shadow-md sm:rounded-lg max-w-2xl mt-2'>
                <table className="w-full text-sm text-left text-gray-500">
                  <thead className="text-xs text-gray-700 uppercase bg-gray-50 ">
                    <tr className="border-b-4 border-gray-600">
                        <th scope="col" className="px-6 py-3"><span className="sr-only">Fav</span></th>
                        <th scope="col" className="px-6 py-3">Nombre</th>
                        <th scope="col" className="px-6 py-3">Fecha Creación</th>
                        <th scope="col" className="px-6 py-3">Fecha Modificación</th>
                        <th scope="col" className="px-6 py-3"><span className="sr-only">Acciones</span></th>
                    </tr>
                  </thead>

                  <tbody className='bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600'>
                    {plans?.map((plan: LowDetailPlanView) => {
                      return (
                              <CurriculumListRow
                                key={plan.id}
                                handleDelete={(id: string) => { setPopUpAlert({ isOpen: true, id }) }}
                                curriculum={plan}
                                handleFavourite ={handleFavourite}
                                openPlanNameModal={openEditModal}
                              />
                      )
                    })}
                  </tbody>

                </table>
                </div>}
          </div>
      </div>

  )
}

export default CurriculumList
