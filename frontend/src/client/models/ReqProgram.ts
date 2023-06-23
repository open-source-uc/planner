/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Express that this course requires the student to belong to a particular program.
 */
export type ReqProgram = {
    hash?: Blob;
    expr?: 'program';
    program: string;
    equal: boolean;
};

