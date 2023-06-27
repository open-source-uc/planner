/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { EquivalenceId } from './EquivalenceId';

export type ConcreteId = {
    is_concrete?: boolean;
    code: string;
    equivalence?: EquivalenceId;
    failed?: string;
};

