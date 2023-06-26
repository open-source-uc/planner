/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ConcreteId } from './ConcreteId';
import type { EquivalenceId } from './EquivalenceId';

/**
 * Indicates that there are some courses missing to fulfill the chosen curriculum.
 * The incomplete block is given in `block`, and the amount of credits missing in
 * `credits`.
 * A set of courses that would fill this block (possibly equivalences) is given in
 * `recommend`.
 */
export type CurriculumErr = {
    kind?: 'curr';
    associated_to?: null;
    is_err?: boolean;
    block: Array<string>;
    credits: number;
    recommend: Array<(ConcreteId | EquivalenceId)>;
};

