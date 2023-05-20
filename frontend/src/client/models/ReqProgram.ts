/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Express that this course requires the student to belong to a particular program.
 */
export type ReqProgram = {
    hash?: Blob;
    expr?: ReqProgram.expr;
    program: string;
    equal: boolean;
};

export namespace ReqProgram {

    export enum expr {
        PROGRAM = 'program',
    }


}

