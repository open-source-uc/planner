/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { Diagnostic } from './Diagnostic';

/**
 * Simply a list of diagnostics, in the same order that is shown to the user.
 */
export type ValidationResult = {
    diagnostics: Array<Diagnostic>;
};

