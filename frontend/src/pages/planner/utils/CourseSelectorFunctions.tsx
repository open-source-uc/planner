function hasDuplicateCourse (semester: CourseId[], selection: string): boolean {
  const semesterClasses = semester.flat()
  return semesterClasses.some((existingCourse) => existingCourse.code === selection)
}

function updateValidatablePlan (index: number, selection: string, details: CourseDetails): void {
  const newValidatablePlan = { ...validatablePlan, classes: [...validatablePlan.classes] }
  newValidatablePlan.classes[modalData.semester] = [...newValidatablePlan.classes[modalData.semester]]

  const equivalence = getEquivalence(index, details)
  newValidatablePlan.classes[modalData.semester][index] = {
    is_concrete: true,
    code: selection,
    equivalence
  }

  if (equivalence !== undefined && equivalence.credits !== details.credits) {
    handleCreditsExceedance(newValidatablePlan, modalData.semester, index, selection, equivalence, details.credits)
  }

  setValidatablePlan(newValidatablePlan)
}

function getEquivalence (index: number, details: CourseDetails): Equivalence | undefined {
  const pastClass = validatablePlan.classes[modalData.semester][index]
  const oldEquivalence = 'credits' in pastClass ? pastClass : pastClass.equivalence

  return {
    is_concrete: true,
    code: selection,
    equivalence: oldEquivalence
  }
}

function handleCreditsExceedance (
  newValidatablePlan: ValidatablePlan,
  semester: number,
  index: number,
  selection: string,
  equivalence: Equivalence | undefined,
  credits: number
): void {
  const semesterClasses = newValidatablePlan.classes[semester]
  let extra = credits - equivalence.credits

  for (let i = semesterClasses.length; i-- > 0;) {
    const equiv = semesterClasses[i]
    if ('credits' in equiv && equiv.code === equivalence.code) {
      if (equiv.credits <= extra) {
        // Consume this equivalence entirely
        semesterClasses.splice(i, 1)
        extra -= equiv.credits
      } else {
        // Consume part of this equivalence
        equiv.credits -= extra
        extra = 0
      }
    }
  }

  newValidatablePlan.classes[semester].splice(index, 1, {
    is_concrete: true,
    code: selection,
    equivalence: {
      ...equivalence,
      credits
    }
  })
}
