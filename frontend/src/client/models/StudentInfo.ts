/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ConcreteId } from './ConcreteId';
import type { EquivalenceId } from './EquivalenceId';

export type StudentInfo = {
    full_name: string;
    cyear: string;
    is_cyear_supported: boolean;
    /**
     * A major code, eg. `M072` for hydraulic engineering.
     */
    reported_major?: string;
    /**
     * A minor code, eg. `N204` for numerical analysis.
     */
    reported_minor?: string;
    /**
     * A title code, eg. `40007` for a computer engineering.
     */
    reported_title?: string;
    passed_courses: Array<Array<(ConcreteId | EquivalenceId)>>;
    current_semester: number;
    next_semester: number;
    admission?: Array<any>;
};

