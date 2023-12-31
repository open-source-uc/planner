import { type CurriculumSpec, type ValidatablePlan, DefaultService } from '../../../client'
import { type CurriculumData } from './Types'

function listToRecord<T> (list: Array<T & { code: string }>): Record<string, T> {
  const dict: Record<string, T> = {}
  for (const item of list) {
    dict[item.code] = item
  }
  return dict
}

export const loadCurriculumsData = async (cYear: string, setCurriculumData: Function, cMajor?: string): Promise<void> => {
  const newCurriculum = await getCurriculumsData(cYear, cMajor)
  setCurriculumData(newCurriculum)
}

export const getCurriculumsData = async (cYear: string, cMajor?: string, curriculumData?: CurriculumData): Promise<CurriculumData> => {
  const { majors, minors, titles } = await (async () => {
    if (curriculumData != null && curriculumData.ofCyear === cYear) {
      if (curriculumData.ofMajor === cMajor) {
        return curriculumData
      } else {
        return {
          majors: curriculumData.majors,
          minors: listToRecord(await DefaultService.getMinors(cYear, cMajor)),
          titles: curriculumData.titles
        }
      }
    } else {
      const response = await DefaultService.getOffer(cYear, cMajor)
      return {
        majors: listToRecord(response.majors),
        minors: listToRecord(response.minors),
        titles: listToRecord(response.titles)
      }
    }
  })()
  return {
    majors,
    minors,
    titles,
    ofMajor: cMajor,
    ofCyear: cYear
  }
}

/**
 * Return a valid curriculum with the new major, minor and title
 */
export const updateCurriculum = (prev: ValidatablePlan | null, key: keyof CurriculumSpec, value: string | undefined, isMinorValid: boolean): ValidatablePlan | null => {
  if (prev == null || prev.curriculum[key] === value) return prev
  const newCurriculum = { ...prev.curriculum, [key]: value }
  if (!isMinorValid) {
    newCurriculum.minor = undefined
  }
  return { ...prev, curriculum: newCurriculum }
}

/**
   * Check if the new minor is valid for the new major
   */
export const isMinorValid = async (
  cyear: string,
  major: string | undefined,
  minor: string | undefined | null
): Promise<boolean> => {
  const newMinors = await DefaultService.getMinors(cyear, major)
  const isValidMinor =
      minor === null ||
      minor === undefined ||
      newMinors.some((m) => m.code === minor)
  return isValidMinor
}

/**
   * Check if the new major is valid for the new cyear
   */
export const isMajorValid = async (
  cyear: string,
  major: string | undefined | null
): Promise<boolean> => {
  const newMajors = await DefaultService.getMajors(cyear)
  const isValidMajor =
      major === null ||
      major === undefined ||
      newMajors.some((m) => m.code === major)

  return isValidMajor
}
