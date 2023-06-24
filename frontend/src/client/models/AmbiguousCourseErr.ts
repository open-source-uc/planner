/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ClassId } from './ClassId';

/**
 * Indicates that some equivalences (`associated_to`) should be disambiguated and they
 * aren't.
 */
export type AmbiguousCourseErr = {
    kind?: 'equiv';
    associated_to: Array<ClassId>;
    is_err?: boolean;
};

