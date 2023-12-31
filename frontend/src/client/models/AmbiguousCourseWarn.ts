/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ClassId } from './ClassId';

/**
 * Indicates that some equivalences (`associated_to`) should be disambiguated and they
 * aren't.
 */
export type AmbiguousCourseWarn = {
    is_err?: boolean;
    kind?: 'equiv';
    associated_to: Array<ClassId>;
};

