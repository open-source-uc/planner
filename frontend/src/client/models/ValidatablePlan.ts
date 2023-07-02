/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ConcreteId } from './ConcreteId';
import type { CurriculumSpec } from './CurriculumSpec';
import type { EquivalenceId } from './EquivalenceId';
import type { Level } from './Level';

/**
 * An academic plan submitted by a user.
 * Contains all of the courses they have passed and intend to pass.
 * Also contains all of the context associated with the user (e.g. their choice of
 * major and minor).
 *
 * Including user context here allows plans to be validated without external context,
 * allowing guests to simulate any plans they want to try out.
 */
export type ValidatablePlan = {
    classes: Array<Array<(ConcreteId | EquivalenceId)>>;
    level?: Level;
    school?: string;
    program?: string;
    career?: string;
    curriculum: CurriculumSpec;
};

