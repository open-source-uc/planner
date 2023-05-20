/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Require the student to have taken a course in the previous semesters.
 */
export type ReqCourse = {
    hash?: Blob;
    expr?: ReqCourse.expr;
    code: string;
    coreq: boolean;
};

export namespace ReqCourse {

    export enum expr {
        REQ = 'req',
    }


}

