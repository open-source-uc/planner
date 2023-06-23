/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { CurriculumSpec } from './CurriculumSpec';

/**
 * Indicates that no major or minor is chosen, and it should be chosen to validate the
 * plan correctly.
 */
export type NoMajorMinorWarn = {
    kind?: 'nomajor';
    associated_to?: null;
    is_err?: boolean;
    plan: CurriculumSpec;
};

