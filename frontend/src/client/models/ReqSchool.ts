/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Express that this course requires the student to belong to a particular school.
 */
export type ReqSchool = {
    expr?: 'school';
    school: string;
    equal: boolean;
};

