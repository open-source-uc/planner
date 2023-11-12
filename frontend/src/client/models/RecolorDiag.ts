/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ClassId } from './ClassId';
import type { EquivalenceId } from './EquivalenceId';

/**
 * Indicates that reassigning the equivalences that are attached to the courses could
 * save some unnecessary classes.
 * Reassigning the attached equivalences is informally referred to as "recoloring".
 *
 * `recolor_as` has the same length as `associated_to`, and indicated which
 * equivalence should be assigned to which course, respectively.
 */
export type RecolorDiag = {
    is_err: boolean;
    kind?: 'recolor';
    associated_to: Array<ClassId>;
    recolor_as: Array<EquivalenceId>;
};

