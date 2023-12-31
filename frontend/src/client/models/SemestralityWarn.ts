/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ClassId } from './ClassId';

/**
 * Indicates that some courses (`associated_to`) are not normally given in the
 * semester they are in.
 * Instead, they are usually only given in semesters with parity `only_available_on`.
 */
export type SemestralityWarn = {
    is_err?: boolean;
    kind?: 'sem';
    associated_to: Array<ClassId>;
    only_available_on: number;
};

