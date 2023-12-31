/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Indicates that the plan is validating for a cyear (`plan`) that does not match the
 * user's cyear (`user`).
 */
export type MismatchedCyearErr = {
    is_err?: boolean;
    kind?: 'cyear';
    associated_to?: null;
    plan: ('C2020' | 'C2022');
    user: string;
};

