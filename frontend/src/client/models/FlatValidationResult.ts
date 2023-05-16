/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { FlatDiagnostic } from './FlatDiagnostic';

export type FlatValidationResult = {
    diagnostics: Array<FlatDiagnostic>;
    course_superblocks: Array<Array<string>>;
};

