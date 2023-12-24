/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Indicates that some courses (in total `unassigned_credits` credits) have no use in
 * the curriculum.
 */
export type UnassignedWarn = {
    is_err?: boolean;
    kind?: 'useless';
    associated_to?: null;
    unassigned_credits: number;
};

