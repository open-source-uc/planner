/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Represents a Course record
 */
export type Course = {
    code: string;
    name: string;
    credits: number;
    deps?: string;
    program: string;
    school: string;
    area?: string;
    category?: string;
    is_relevant: boolean;
    is_available: boolean;
    semestrality_first: boolean;
    semestrality_second: boolean;
    semestrality_tav: boolean;
};

