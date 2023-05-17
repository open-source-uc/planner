/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { Cyear } from './Cyear';

/**
 * Represents a curriculum specification.
 * This specification should uniquely identify a curriculum, although it contains no
 * information about the curriculum itself.
 */
export type CurriculumSpec = {
    cyear: Cyear;
    major?: string;
    minor?: string;
    title?: string;
};

