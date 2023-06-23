/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Indicates that some courses (in total `unassigned_credits` credits) have no use in
 * the curriculum.
 */
export type UnassignedWarn = {
    kind?: 'useless';
    associated_to?: null;
    is_err?: boolean;
    unassigned_credits: number;
};

