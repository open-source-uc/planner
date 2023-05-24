/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { Const } from './Const';
import type { MinCredits } from './MinCredits';
import type { Or } from './Or';
import type { ReqCareer } from './ReqCareer';
import type { ReqCourse } from './ReqCourse';
import type { ReqLevel } from './ReqLevel';
import type { ReqProgram } from './ReqProgram';
import type { ReqSchool } from './ReqSchool';

/**
 * Logical AND connector.
 * Only satisfied if all of its children are satisfied.
 */
export type And = {
    hash?: Blob;
    children: Array<(And | Or | Const | MinCredits | ReqLevel | ReqSchool | ReqProgram | ReqCareer | ReqCourse)>;
    expr?: And.expr;
};

export namespace And {

    export enum expr {
        AND = 'and',
    }


}

