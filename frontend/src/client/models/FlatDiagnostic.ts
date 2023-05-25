/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ClassId } from './ClassId';

export type FlatDiagnostic = {
    class_id?: ClassId;
    is_warning: boolean;
    message: string;
};

