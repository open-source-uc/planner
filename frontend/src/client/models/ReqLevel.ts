/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { Level } from './Level';

/**
 * Express that this course requires a certain academic level.
 */
export type ReqLevel = {
    hash?: Blob;
    expr?: 'lvl';
    min_level: Level;
};

