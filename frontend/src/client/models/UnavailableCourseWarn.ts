/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ClassId } from './ClassId';

/**
 * Indicates that some courses (`associated_to`) have not been given in a long while
 * and are probably unavailable.
 */
export type UnavailableCourseWarn = {
    is_err?: boolean;
    kind?: 'unavail';
    associated_to: Array<ClassId>;
};

