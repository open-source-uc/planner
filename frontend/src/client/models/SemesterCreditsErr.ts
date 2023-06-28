/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Indicates that some semesters (`associated_to`) have more than the allowed amount
 * of credits.
 */
export type SemesterCreditsErr = {
    kind?: 'creditserr';
    associated_to: Array<number>;
    is_err?: boolean;
    max_allowed: number;
    actual: number;
};

