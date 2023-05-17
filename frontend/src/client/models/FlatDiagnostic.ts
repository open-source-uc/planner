/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ClassIndex } from './ClassIndex';

export type FlatDiagnostic = {
    course_index?: ClassIndex;
    is_warning: boolean;
    message: string;
};

