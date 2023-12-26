/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ClassId } from './ClassId';

/**
 * Indicates that some courses (`associated_to`) have unknown/invalid codes.
 */
export type UnknownCourseErr = {
    is_err?: boolean;
    kind?: 'unknown';
    associated_to: Array<ClassId>;
};

