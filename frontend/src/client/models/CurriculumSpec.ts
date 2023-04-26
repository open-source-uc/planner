/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { Cyear } from './Cyear';

/**
 * Represents a curriculum specification.
 * This specification should uniquely specify a curriculum.
 */
export type CurriculumSpec = {
    cyear: Cyear;
    major?: string;
    minor?: string;
    title?: string;
};

