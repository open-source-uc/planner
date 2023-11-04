/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Indicates that some semesters (`associated_to`) have more than the recommended
 * amount of credits.
 */
export type SemesterCreditsWarn = {
    is_err?: boolean;
    kind?: 'creditswarn';
    associated_to: Array<number>;
    max_recommended: number;
    actual: number;
};

