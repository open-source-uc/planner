/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { AmbiguousCourseErr } from './AmbiguousCourseErr';
import type { CourseRequirementErr } from './CourseRequirementErr';
import type { CurriculumErr } from './CurriculumErr';
import type { MismatchedCurriculumSelectionWarn } from './MismatchedCurriculumSelectionWarn';
import type { MismatchedCyearErr } from './MismatchedCyearErr';
import type { NoMajorMinorWarn } from './NoMajorMinorWarn';
import type { OutdatedCurrentSemesterErr } from './OutdatedCurrentSemesterErr';
import type { OutdatedPlanErr } from './OutdatedPlanErr';
import type { SemesterCreditsErr } from './SemesterCreditsErr';
import type { SemesterCreditsWarn } from './SemesterCreditsWarn';
import type { SemestralityWarn } from './SemestralityWarn';
import type { UnassignedWarn } from './UnassignedWarn';
import type { UnavailableCourseWarn } from './UnavailableCourseWarn';
import type { UnknownCourseErr } from './UnknownCourseErr';

export type ValidationResult = {
    diagnostics: Array<(CourseRequirementErr | UnknownCourseErr | MismatchedCyearErr | MismatchedCurriculumSelectionWarn | OutdatedPlanErr | OutdatedCurrentSemesterErr | SemestralityWarn | UnavailableCourseWarn | AmbiguousCourseErr | SemesterCreditsWarn | SemesterCreditsErr | CurriculumErr | UnassignedWarn | NoMajorMinorWarn)>;
    course_superblocks: Record<string, Array<string>>;
};

