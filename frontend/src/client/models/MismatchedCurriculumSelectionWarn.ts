/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { CurriculumSpec } from './CurriculumSpec';

/**
 * Indicates that the plan selection of curriculum does not match the official
 * curriculum declaration.
 */
export type MismatchedCurriculumSelectionWarn = {
    is_err?: boolean;
    kind?: 'currdecl';
    associated_to?: null;
    plan: CurriculumSpec;
    user: CurriculumSpec;
};

