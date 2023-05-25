/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Express that this course requires the student to belong to a particular school.
 */
export type ReqSchool = {
    hash?: Blob;
    expr?: ReqSchool.expr;
    school: string;
    equal: boolean;
};

export namespace ReqSchool {

    export enum expr {
        SCHOOL = 'school',
    }


}

