/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Indicates that some semesters (`associated_to`) have more than the recommended or
 * allowed amount of credits.
 *
 * If `is_err` is `True`, the hard limit was surpassed.
 * If `is_err` is `False`, only the soft limit was surpassed.
 */
export type SemesterCreditsDiag = {
    is_err: boolean;
    kind?: 'credits';
    associated_to: Array<number>;
    credit_limit: number;
    actual: number;
};

