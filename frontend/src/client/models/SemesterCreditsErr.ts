/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Indicates that some semesters (`associated_to`) have more than the allowed amount
 * of credits.
 */
export type SemesterCreditsErr = {
    is_err?: boolean;
    kind?: 'creditserr';
    associated_to: Array<number>;
    max_allowed: number;
    actual: number;
};

