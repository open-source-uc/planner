/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Details about an equivalence.
 * - code: Unique code identifying this equivalence.
 * Unique across course and equivalence codes (ie. course and equivalence names
 * live in the same namespace).
 * - name: Informative name of this equivalence.
 * - is_homogeneous: Indicates whether this equivalence is "homogeneous".
 * A homogeneous equivalence is one where all of its concrete courses have the
 * same requirements and reverse requirements (eg. "Dinamica" is homogeneous, but
 * "OFG" is not).
 * The requirement validator gives up on non-homogeneous equivalences, but tries
 * to validate homogeneous dependencies.
 * - is_unessential: Whether the equivalence can go unspecified without raising an
 * error.
 * - courses: List of concrete course codes that make up this equivalence.
 */
export type EquivDetails = {
    code: string;
    name: string;
    is_homogeneous: boolean;
    is_unessential: boolean;
    courses: Array<string>;
};

