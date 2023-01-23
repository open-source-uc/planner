/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ConcreteId } from './ConcreteId';
import type { EquivalenceId } from './EquivalenceId';
import type { Level } from './Level';

/**
 * Raw plan submitted by a user.
 * Also contains context about the user.
 * `ValidatablePlan` should represent any user & plan configuration.
 */
export type ValidatablePlan = {
    classes: Array<Array<(ConcreteId | EquivalenceId)>>;
    next_semester: number;
    level?: Level;
    school?: string;
    program?: string;
    career?: string;
};

