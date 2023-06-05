/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { CurriculumSpec } from './CurriculumSpec';

/**
 * Indicates that the plan selection of curriculum does not match the official
 * curriculum declaration.
 */
export type MismatchedCurriculumSelectionWarn = {
    kind?: 'currdecl';
    associated_to?: null;
    is_err?: boolean;
    plan: CurriculumSpec;
    user: CurriculumSpec;
};

