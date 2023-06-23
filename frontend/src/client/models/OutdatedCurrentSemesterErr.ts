/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Indicates that the current semester in the plan does not reflect the courses that
 * the user is currently taken.
 * This could be because the user is experimenting with modifying their current
 * semester (ie. removing courses that they don't expect to pass).
 * This is the "smaller version" of `OutdatedPlanErr`.
 */
export type OutdatedCurrentSemesterErr = {
    kind?: 'outdatedcurrent';
    associated_to: Array<number>;
    is_err?: boolean;
};

