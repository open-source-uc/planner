/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { Cyear } from './Cyear';

/**
 * Indicates that the plan is validating for a cyear (`plan`) that does not match the
 * user's cyear (`user`).
 */
export type MismatchedCyearErr = {
    kind?: 'cyear';
    associated_to?: null;
    is_err?: boolean;
    plan: Cyear;
    user: string;
};

