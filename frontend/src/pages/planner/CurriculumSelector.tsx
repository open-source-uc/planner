import { Fragment, memo, useEffect } from 'react'
import { Listbox, Transition } from '@headlessui/react'
import { type Major, type Minor, type Title, type CurriculumSpec } from '../../client'
import { type CurriculumData } from './utils/Types'
import { toast } from 'react-toastify'

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
  canDeselect: boolean
  data: Record<string, Major | Minor | Title>
  value: string | null | undefined
  onChange: (value: string) => void
}

const Selector = memo(function _Selector ({
  canDeselect,
  data,
  value,
  onChange
}: SelectorProps): JSX.Element {
  const selectedOption = value !== undefined && value !== null ? (data[value] ?? { name: 'Minor desconocido', code: value }) : { name: 'Por Seleccionar', code: null }
  if (value !== undefined && value !== null && data[value] === undefined) {
    useEffect(() => {
      toast.warn('Tu minor todavía no está soportado oficialmente. Los cursos pueden estar incorrectos, revisa dos veces.', {
        toastId: 'MINOR_NOT_SUPPORTED',
        autoClose: false,
        position: 'bottom-left'
      })
    }, [value])
  }
  return (
    <Listbox value={selectedOption.code} onChange={onChange}>
      <Listbox.Button className="selectorButton">
        <span className="inline truncate">
          {selectedOption.name} {selectedOption.code !== null && `(${selectedOption.code})`}
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
  return (
      <ul className={'curriculumSelector'}>
        <li className={'selectorElement'}>
          <div className={'selectorName'}>Major:</div>
          {curriculumData != null
            ? <Selector
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
            canDeselect={true}
              data={curriculumData.titles}
              value={curriculumSpec.title}
              onChange={(t) => selectTitle(t)}
            />
          }
        </li>
        <li className={'selectorElement'}>
          <div className={'selectorName'}>Año Curriculum:</div>
          {curriculumData != null &&
            <Listbox value={curriculumSpec.cyear?.raw} onChange={(t) => selectYear(t)}>
            <Listbox.Button className="selectorButton">
              <span className="inline truncate">
                {curriculumSpec.cyear?.raw}
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
              <Listbox.Options className="curriculumOptions z-40 w-40">
                  <Listbox.Option
                    className={({ active }) =>
                      `curriculumOption ${active ? 'bg-place-holder text-amber-800' : 'text-gray-900'}`
                    }
                    value={'C2022'}
                  >
                  {({ selected }) => (
                    <>
                      <span className={'block truncate font-medium  '}>
                        C2022
                      </span>
                      {selected ? <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-800">*</span> : null}
                    </>
                  )}
                </Listbox.Option>
                <Listbox.Option
                  className={({ active }) =>
                    `curriculumOption ${active ? 'bg-place-holder text-amber-800' : 'text-gray-900'}`
                  }
                  value={'C2020'}
                >
                  {({ selected }) => (
                    <>
                      <span
                        className={`block truncate ${selected ? 'font-medium text-black' : 'font-normal'}`}
                      >
                        C2020
                      </span>
                      {selected ? <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-800">*</span> : null}
                    </>
                  )}
                </Listbox.Option>
              </Listbox.Options>
            </Transition>
          </Listbox>
          }
        </li>
        {planName !== '' && <li className={'inline text-md ml-3 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Plan:</div> {planName}</li>}
      </ul>
  )
})

export default CurriculumSelector
