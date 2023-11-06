/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { And } from './And';
import type { Const } from './Const';
import type { MinCredits } from './MinCredits';
import type { ReqCareer } from './ReqCareer';
import type { ReqCourse } from './ReqCourse';
import type { ReqLevel } from './ReqLevel';
import type { ReqProgram } from './ReqProgram';
import type { ReqSchool } from './ReqSchool';

/**
 * Logical OR connector.
 * Only satisfied if at least one of its children is satisfied.
 */
export type Or = {
    expr?: 'or';
    children: Array<(And | Or | Const | MinCredits | ReqLevel | ReqSchool | ReqProgram | ReqCareer | ReqCourse)>;
};

