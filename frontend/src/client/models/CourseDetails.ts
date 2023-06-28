/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { And } from './And';
import type { Const } from './Const';
import type { MinCredits } from './MinCredits';
import type { Or } from './Or';
import type { ReqCareer } from './ReqCareer';
import type { ReqCourse } from './ReqCourse';
import type { ReqLevel } from './ReqLevel';
import type { ReqProgram } from './ReqProgram';
import type { ReqSchool } from './ReqSchool';

export type CourseDetails = {
    code: string;
    name: string;
    credits: number;
    deps: (And | Or | Const | MinCredits | ReqLevel | ReqSchool | ReqProgram | ReqCareer | ReqCourse);
    banner_equivs: Array<string>;
    canonical_equiv: string;
    program: string;
    school: string;
    area?: string;
    category?: string;
    is_available: boolean;
    semestrality: Array<any>;
};

