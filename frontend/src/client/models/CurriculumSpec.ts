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
    /**
     * The curriculum version.
     */
    cyear: Cyear;
    /**
     * A major code, eg. `M072` for hydraulic engineering.
     */
    major?: string;
    /**
     * A minor code, eg. `N204` for numerical analysis.
     */
    minor?: string;
    /**
     * A title code, eg. `40007` for a computer engineering.
     */
    title?: string;
};

