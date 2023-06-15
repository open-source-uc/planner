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
 */
export type CourseRequirementErr = {
    kind?: 'req';
    associated_to: Array<ClassId>;
    is_err?: boolean;
    missing: (And | Or | Const | MinCredits | ReqLevel | ReqSchool | ReqProgram | ReqCareer | ReqCourse);
    modernized_missing: (And | Or | Const | MinCredits | ReqLevel | ReqSchool | ReqProgram | ReqCareer | ReqCourse);
};

