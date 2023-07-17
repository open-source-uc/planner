/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * A curriculum version, constrained to whatever curriculum versions we support.
 * Whenever something depends on the version of the curriculum, it should match
 * exhaustively on the `raw` field (using Python's `match` statement).
 * This allows the linter to pinpoint all places that need to be updated whenever a
 * new curriculum version is added.
 *
 * NOTE: Remember to reset the cache in the database after any changes, either manually
 * or through migrations.
 */
export type Cyear = {
    raw: ('C2020' | 'C2022');
};

