/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * A restriction that is only satisfied if the total amount of credits in the previous
 * semesters is over a certain threshold.
 */
export type MinCredits = {
    hash?: Blob;
    expr?: 'cred';
    min_credits: number;
};

