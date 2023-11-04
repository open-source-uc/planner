/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Express that this course requires the student to belong to a particular career.
 */
export type ReqCareer = {
    expr?: 'career';
    career: string;
    equal: boolean;
};

