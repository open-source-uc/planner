import { Fragment, useState, useEffect, memo } from 'react'
import { Listbox, Transition } from '@headlessui/react'
import { Major, Minor, Title, DefaultService, CurriculumSpec } from '../../client'

interface CurriculumData {
  majors: { [code: string]: Major }
  minors: { [code: string]: Minor }
  titles: { [code: string]: Title }
}

interface CurriculumSelectorProps {
  planName: String
  curriculumSpec: CurriculumSpec | { cyear: null, major: null, minor: null, title: null }
  selectMajor: Function
  selectMinor: Function
  selectTitle: Function
}

/**
 * The selector of major, minor and tittle.
 */
const CurriculumSelector = memo(function CurriculumSelector ({
  planName,
  curriculumSpec,
  selectMajor,
  selectMinor,
  selectTitle
}: CurriculumSelectorProps): JSX.Element {
  const [curriculumData, setCurriculumData] = useState<CurriculumData | null>(null)
  async function loadCurriculumsData (cYear: string, cMajor?: string): Promise<void> {
    const [majors, minors, titles] = await Promise.all([
      DefaultService.getMajors(cYear),
      DefaultService.getMinors(cYear, cMajor),
      DefaultService.getTitles(cYear)
    ])
    const curriculumData: CurriculumData = {
      majors: majors.reduce((dict: { [code: string]: Major }, m: Major) => {
        dict[m.code] = m
        return dict
      }, {}),
      minors: minors.reduce((dict: { [code: string]: Minor }, m: Minor) => {
        dict[m.code] = m
        return dict
      }, {}),
      titles: titles.reduce((dict: { [code: string]: Title }, t: Title) => {
        dict[t.code] = t
        return dict
      }, {})
    }
    setCurriculumData(curriculumData)
  }

  useEffect(() => {
    if (curriculumSpec.cyear !== null) {
      void loadCurriculumsData(curriculumSpec.cyear.raw, curriculumSpec.major)
    }
  }, [curriculumSpec])
  return (
      <ul className={'curriculumSelector'}>
        <li className={'selectorElement'}>
          <div className={'selectorName'}>Major:</div>
          {curriculumData != null &&
            <Listbox value={curriculumSpec.major !== undefined && curriculumSpec.major !== null ? curriculumData.majors[curriculumSpec.major] : {}} onChange={(m) => selectMajor(m)}>
              <Listbox.Button className={'selectorButton'}>
                <span className="inline truncate">{curriculumSpec.major !== undefined && curriculumSpec.major !== null ? curriculumData.majors[curriculumSpec.major]?.name : 'Por elegir'}</span>
                <svg className="inline" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
                  <path fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M7 10l5 5 5-5"/>
                </svg>
              </Listbox.Button>
              <Transition
                as={Fragment}
                leave="transition ease-in duration-10 b0"
                leaveFrom="opacity-100"
                leaveTo="opacity-0"
              >
                <Listbox.Options className={'curriculumOptions'} style={{ zIndex: 1 }}>
                  {Object.keys(curriculumData.majors).map((key) => (
                    <Listbox.Option
                      className={({ active }) =>
                      `curriculumOption ${
                        active ? 'bg-place-holder text-amber-800' : 'text-gray-900'
                      }`
                      }key={key}
                      value={curriculumData.majors[key]}
                    >
                      {({ selected }) => (
                        <>
                          <span
                            className={`block truncate ${
                              selected ? 'font-medium text-black' : 'font-normal'
                            }`}
                          >
                            {curriculumData.majors[key].name}
                          </span>
                          {selected
                            ? (
                            <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-800">
                              *
                            </span>
                              )
                            : null}
                        </>
                      )}
                    </Listbox.Option>
                  ))}
                </Listbox.Options>
              </Transition>
            </Listbox>
          }
        </li>
        <li className={'selectorElement'}>
          <div className={'selectorName'}>Minor:</div>
          {curriculumData != null &&
            <Listbox
              value={curriculumSpec.minor !== undefined && curriculumSpec.minor !== null ? curriculumData.minors[curriculumSpec.minor] : {}}
              onChange={(m) => selectMinor(m)}>
              <Listbox.Button className={'selectorButton'}>
                <span className="inline truncate">{curriculumSpec.minor !== undefined && curriculumSpec.minor !== null ? curriculumData.minors[curriculumSpec.minor]?.name : 'Por elegir'}</span>
                <svg className="inline" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
                  <path fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M7 10l5 5 5-5"/>
                </svg>
              </Listbox.Button>
              <Transition
                as={Fragment}
                leave="transition ease-in duration-100"
                leaveFrom="opacity-100"
                leaveTo="opacity-0"
              >
                <Listbox.Options className={'curriculumOptions'} style={{ zIndex: 1 }}>
                  { Object.keys(curriculumData.minors).map((key) => (
                    <Listbox.Option
                      className={({ active }) =>
                        `curriculumOption ${
                          active ? 'bg-place-holder text-amber-800' : 'text-gray-900'
                        }`
                      }key={key}
                      value={curriculumData.minors[key]}
                    >
                      {({ selected }) => (
                        <>
                          <span
                            className={`block truncate ${
                              selected ? 'font-medium text-black' : 'font-normal'
                            }`}
                          >
                            {curriculumData.minors[key].name}
                          </span>
                          {selected
                            ? (
                            <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-800">
                              *
                            </span>
                              )
                            : null}
                        </>
                      )}
                    </Listbox.Option>
                  ))}
                </Listbox.Options>
              </Transition>
            </Listbox>
          }
        </li>
        <li className={'selectorElement'}>
          <div className={'selectorName'}>Titulo:</div>
          {curriculumData != null &&
          <Listbox value={(curriculumData != null) && curriculumSpec.title !== undefined && curriculumSpec.title !== null ? curriculumData.titles[curriculumSpec.title] : {}} onChange={(t) => selectTitle(t)}>
            <Listbox.Button className="selectorButton">
              <span className="inline truncate">{curriculumSpec.title !== undefined && curriculumSpec.title !== null ? curriculumData.titles[curriculumSpec.title]?.name : 'Por elegir'}</span>
              <svg className="inline" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
                  <path fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M7 10l5 5 5-5"/>
                </svg>
            </Listbox.Button>
            <Transition
              as={Fragment}
              leave="transition ease-in duration-100"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <Listbox.Options className={'curriculumOptions'} style={{ zIndex: 1 }}>
                {Object.keys(curriculumData.titles).map((key) => (
                  <Listbox.Option
                    className={({ active }) =>
                    `curriculumOption ${
                      active ? 'bg-place-holder text-amber-800' : ''
                    }`
                    }key={key}
                    value={curriculumData.titles[key]}
                  >
                    {({ selected }) => (
                      <>
                        <span
                          className={`block truncate ${
                            selected ? 'font-medium text-black' : 'font-normal'
                          }`}
                        >
                          {curriculumData.titles[key].name}
                        </span>
                        {selected
                          ? (
                          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-800">
                            *
                          </span>
                            )
                          : null}
                      </>
                    )}
                  </Listbox.Option>
                ))}
              </Listbox.Options>
            </Transition>
          </Listbox>
          }
        </li>
        {planName !== '' && <li className={'inline text-md ml-5 font-semibold'}><div className={'text-sm inline mr-1 font-normal'}>Plan:</div> {planName}</li>}
      </ul>
  )
})

export default CurriculumSelector
