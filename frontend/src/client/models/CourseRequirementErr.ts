/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { And } from './And';
import type { ClassId } from './ClassId';
import type { Const } from './Const';
import type { MinCredits } from './MinCredits';
import type { Or } from './Or';
import type { ReqCareer } from './ReqCareer';
import type { ReqCourse } from './ReqCourse';
import type { ReqLevel } from './ReqLevel';
import type { ReqProgram } from './ReqProgram';
import type { ReqSchool } from './ReqSchool';

/**
 * Indicates that a course (`associated_to`) is missing some requirements (`missing`).
 *
 * - `missing`: The raw missing requirements, as specified in the course requirements.
 * This expression is simplified, and only contains the courses that are actually
 * missing.
 * - `missing_modernized`: Like `missing`, but course codes are replaced by their
 * modernized counterparts.
 * - `push_back`: If the `associated_to` course can be moved back some semesters an
 * then fulfill the requirements, this property is the index of that semester.
 * - `pull_forward`: If some requirements already exist in the plan but they are too
 * late to count as requirements for the `associate_to` course, they are listed
 * here, along with the semester that they would have to be moved to.
 * - `add_absent`: Requirements that are not in the plan and have to be added.
 * The modernized code is listed here.
 */
export type CourseRequirementErr = {
    kind?: 'req';
    associated_to: Array<ClassId>;
    is_err?: boolean;
    missing: (And | Or | Const | MinCredits | ReqLevel | ReqSchool | ReqProgram | ReqCareer | ReqCourse);
    modernized_missing: (And | Or | Const | MinCredits | ReqLevel | ReqSchool | ReqProgram | ReqCareer | ReqCourse);
    push_back?: number;
    pull_forward: Record<string, number>;
    add_absent: Record<string, number>;
};

