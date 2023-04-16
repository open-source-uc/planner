/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Represents a curriculum specification.
 * This specification should uniquely specify a curriculum.
 */
export type CurriculumSpec = {
    cyear: CurriculumSpec.cyear;
    major?: string;
    minor?: string;
    title?: string;
};

export namespace CurriculumSpec {

    export enum cyear {
        C2020 = 'C2020',
    }


}

