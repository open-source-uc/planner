/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * A curriculum version, constrained to whatever curriculum versions we support.
 * Whenever something depends on the version of the curriculum, it should match
 * exhaustively on the `__root__` field (using Python's `match` statement).
 * This allows the linter to pinpoint all places that need to be updated whenever a
 * new curriculum version is added.
 */
export enum Cyear {
    C2020 = 'C2020',
}
