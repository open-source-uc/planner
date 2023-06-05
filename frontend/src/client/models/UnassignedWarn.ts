/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ClassId } from './ClassId';

/**
 * Indicates that some courses (`associated_to`) have no use in the curriculum.
 */
export type UnassignedWarn = {
    kind?: 'useless';
    associated_to: Array<ClassId>;
    is_err?: boolean;
};

