/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ConcreteId } from './ConcreteId';
import type { EquivalenceId } from './EquivalenceId';

/**
 * Indicates that the plan does not reflect the courses that the user has taken.
 * This could happen if the user planned ahead, but didn't follow their plan.
 * Afterwards, when they take different courses than they planned, their plan becomes
 * outdated.
 * The semesters that are mismatched are included in `associated_to`.
 * Each mismatched semester contains an associated entry in `replace_with` with the
 * courses that should replace this semester.
 * If `is_current` is true, then the only outdated semester is the current semester,
 * which may be a special case if the user is trying out changes to their current
 * semester.
 */
export type OutdatedPlanErr = {
    is_err?: boolean;
    kind?: 'outdated';
    associated_to: Array<number>;
    replace_with: Array<Array<(ConcreteId | EquivalenceId)>>;
    is_current: boolean;
};

