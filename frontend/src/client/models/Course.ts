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
};

