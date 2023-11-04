/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Indicates that the plan does not reflect the courses that the user has taken.
 * This could happen if the user planned ahead, but didn't follow their plan.
 * Afterwards, when they take different courses than they planned, their plan becomes
 * outdated.
 * The semesters that are mismatched are included in `associated_to`.
 */
export type OutdatedPlanErr = {
    is_err?: boolean;
    kind?: 'outdated';
    associated_to: Array<number>;
};

