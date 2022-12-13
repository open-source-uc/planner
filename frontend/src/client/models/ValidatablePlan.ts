/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { Level } from './Level';

export type ValidatablePlan = {
    classes: Array<Array<string>>;
    next_semester: number;
    level?: Level;
    school?: string;
    program?: string;
    career?: string;
};

