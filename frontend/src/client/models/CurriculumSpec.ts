/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { Cyear } from './Cyear';

/**
 * Represents a curriculum specification.
 * This specification should uniquely identify a curriculum, although it contains no
 * information about the curriculum itself.
 *
 * NOTE: Remember to reset the cache in the database after any changes, either manually
 * or through migrations.
 */
export type CurriculumSpec = {
    cyear: Cyear;
    major?: string;
    minor?: string;
    title?: string;
};

