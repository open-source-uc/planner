import { memo } from 'react'
import { Dialog, Tab } from '@headlessui/react'
import Legend from './Legend'
import Instructions from './Instructions'
import GeneralModal from '../../../components/GeneralModal'

const LegendModal = ({ open, onClose }: { open: boolean, onClose: Function }): JSX.Element => {
  const tabNames = ['Importante', 'Leyenda', 'Instrucciones']

  return (
    <GeneralModal isOpen={open} onClose={onClose}>
      <Dialog.Panel className="w-2/3 px-5 py-6 bg-slate-100 border-slate-300 overflow-hidden transform  rounded-2xl border-2 text-left align-middle shadow-xl transition-all">
          <Dialog.Title as="h3" className="text-2xl font-medium leading-6 text-gray-900 mb-3">
            Leyenda e Instrucciones
          </Dialog.Title>

          <div className="w-full p-2">
            <Tab.Group>
              <Tab.List className="flex space-x-1 rounded-xl bg-blue-900/20 p-1">
                {tabNames.map((category: string, index: number) => (
                  <Tab
                    key={category}
                    className={ ({ selected }) =>
                      `w-full rounded-lg py-2.5 text-sm font-medium leading-5 text-blue-700 ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2',
                      ${selected
                        ? 'bg-white shadow'
                        : 'text-blue-100 hover:bg-white/[0.12] hover:text-white'}`
                    }
                  >
                    {category}
                  </Tab>
                ))}
              </Tab.List>
              <Tab.Panels className="mt-2 h-[45vh] overflow-auto">
                <Tab.Panel className='rounded-xl bg-white p-3 min-h-full'>
                  <p className="text-sm text-justify text-gray-500">Esta malla curricular es la recomendada y está sujeta a modificaciones conforme a la planificación académica vigente al momento de inscribir cursos.</p>
                  <p className="text-sm text-justify text-gray-500 my-8">Los requisitos y planificación de los cursos pueden ir variando semestre a semestre. Por lo que Mallas ING puede tener algunas variaciones. La información oficial de los requisitos y planificación de los cursos se encuentra disponible en el catálogo de cursos (http://catalogo.uc.cl/) y el libro de cursos (http://buscacursos.uc.cl/).</p>
                  <p className="text-sm text-justify text-gray-500">Es responsabilidad del alumno verificar que el avance curricular determinado por Mallas ING sea el correcto. Los Planes de Estudios publicados en Siding corresponden a la información oficial y actualizada.</p>
                </Tab.Panel>
                <Tab.Panel className='rounded-xl bg-white p-3 min-h-full'><Legend /></Tab.Panel>
                <Tab.Panel className='rounded-xl bg-white p-3 min-h-full'><Instructions /></Tab.Panel>
              </Tab.Panels>
            </Tab.Group>
          </div>
          <div className="m-2">
            <button
              type="button"
              className="inline-flex float-right justify-center rounded-md border border-transparent bg-blue-100 px-4 py-2 text-sm font-medium text-blue-900 hover:bg-blue-200"
              onClick={() => onClose()}
            >
              Cerrar
            </button>
          </div>
      </Dialog.Panel>
    </GeneralModal>
  )
}

export default memo(LegendModal)
