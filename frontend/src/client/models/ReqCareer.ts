/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Express that this course requires the student to belong to a particular career.
 */
export type ReqCareer = {
    hash?: Blob;
    expr?: ReqCareer.expr;
    career: string;
    equal: boolean;
};

export namespace ReqCareer {

    export enum expr {
        CAREER = 'career',
    }


}

