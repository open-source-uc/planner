import { Fragment, memo, useEffect } from 'react'
import { Listbox, Transition } from '@headlessui/react'
import { type CurriculumSpec } from '../../client'
import { type CurriculumData } from './utils/Types'
import { toast } from 'react-toastify'
import { useAuth } from '../../contexts/auth.context'

interface CurriculumSelectorProps {
  planName: string
  curriculumData: CurriculumData | null
  curriculumSpec: CurriculumSpec | { cyear: null, major: null, minor: null, title: null }
  selectMajor: Function
  selectMinor: Function
  selectTitle: Function
  selectYear: Function
}
interface SelectorProps {
  name: string
  canDeselect: boolean
  data: Record<string, { name: string }>
  value: string | null | undefined
  onChange: (value: string) => void
}

const Selector = memo(function _Selector ({
  name,
  data,
  value,
  canDeselect,
  onChange
}: SelectorProps): JSX.Element {
  const selectedOption = value != null ? (data[value] ?? { name: `${name} Desconocido` }) : { name: 'Por Seleccionar' }
  if (value !== undefined && value !== null && data[value] === undefined) {
    useEffect(() => {
      toast.warn(`Tu ${name} todavía no está soportado oficialmente. Los cursos pueden estar incorrectos, revisa dos veces.`, {
        toastId: `UNSUPPORTED_${name}`,
        autoClose: false,
        position: 'bottom-left'
      })
    }, [value])
  }
  return (
    <Listbox value={value} onChange={onChange}>
      <Listbox.Button className="selectorButton">
        <span className="inline truncate">
          {selectedOption.name} {value != null && `(${value})`}
        </span>
        <svg
          className="inline"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          width="24"
          height="24"
        >
          <path fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M7 10l5 5 5-5"/>
        </svg>
      </Listbox.Button>
      <Transition
        as={Fragment}
        leave="transition ease-in duration-100"
        leaveFrom="opacity-100"
        leaveTo="opacity-0"
      >
        <Listbox.Options className="curriculumOptions z-40">
        {canDeselect && value !== undefined && value !== null &&
            <Listbox.Option
              className={({ active }) =>
                `curriculumOption ${active ? 'bg-place-holder text-amber-800' : 'text-gray-900'}`
              }
              value={undefined}
            >
            {({ selected }) => (
              <>
                <span className={'block truncate font-medium  '}>
                  Eliminar selección
                </span>
                {selected ? <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-800">*</span> : null}
              </>
            )}
          </Listbox.Option>
        }
        <div className="overflow-auto">
        {Object.keys(data).map((key) => (
          <Listbox.Option
            className={({ active }) =>
              `curriculumOption ${active ? 'bg-place-holder text-amber-800' : 'text-gray-900'}`
            }
            key={key}
            value={key}
          >
            {({ selected }) => (
              <>
                <span
                  className={`block truncate ${selected ? 'font-medium text-black' : 'font-normal'}`}
                >
                  {data[key].name} ({key})
                </span>
                {selected
                  ? (
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-800">*</span>
                    )
                  : null}
              </>
            )}
          </Listbox.Option>
        ))}</div>
        </Listbox.Options>
      </Transition>
    </Listbox>
  )
})

/**
 * The selector of major, minor and tittle.
 */
const CurriculumSelector = memo(function CurriculumSelector ({
  planName,
  curriculumData,
  curriculumSpec,
  selectMajor,
  selectMinor,
  selectTitle,
  selectYear
}: CurriculumSelectorProps): JSX.Element {
  const authState = useAuth()
  return (
      <ul className={'curriculumSelector'}>
        <li className={'selectorElement'}>
          <div className={'selectorName'}>Major:</div>
          {curriculumData != null
            ? <Selector
              name="Major"
              canDeselect={false}
              data={curriculumData.majors}
              value={curriculumSpec.major}
              onChange={(t) => selectMajor({ cyear: curriculumData.majors[t].cyear, code: t })}
            />
            : <svg
              className="inline"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              width="24"
              height="24"
            >
              <path fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M7 10l5 5 5-5"/>
            </svg>
          }
        </li>
        <li className={'selectorElement'}>
          <div className={'selectorName'}>Minor:</div>
          {curriculumData != null
            ? <Selector
              name="Minor"
              canDeselect={true}
              data={curriculumData.minors}
              value={curriculumSpec.minor}
              onChange={(t) => selectMinor(t)}
            />
            : <svg
                className="inline"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                width="24"
                height="24"
              >
              <path fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M7 10l5 5 5-5"/>
            </svg>
          }
        </li>
        <li className={'selectorElement'}>
          <div className={'selectorName'}>Titulo:</div>
          {curriculumData != null &&
            <Selector
              name="Título"
              canDeselect={true}
              data={curriculumData.titles}
              value={curriculumSpec.title}
              onChange={(t) => selectTitle(t)}
            />
          }
        </li>
        {
        (authState?.user == null) &&
        <li className={'selectorElement'}>
          <div className={'selectorName'}>Versión Curriculum:</div>
          {curriculumSpec != null &&
            <Selector
              name="Curriculum"
              canDeselect={false}
              data={{
                C2020: { name: 'Admisión 2020 y 2021' },
                C2022: { name: 'Admisión 2022 y posteriores' }
              }}
              value={curriculumSpec.cyear?.raw}
              onChange={(c) => selectYear(c)}
            />
          }
        </li>
        }
        {planName !== '' && <li className={'inline text-md ml-3 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Plan:</div> {planName}</li>}
      </ul>
  )
})

export default CurriculumSelector
