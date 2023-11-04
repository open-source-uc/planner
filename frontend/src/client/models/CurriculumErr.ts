/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Indicates that there are some courses missing to fulfill the chosen curriculum.
 * The incomplete block is given in `block`, and the amount of credits missing in
 * `credits`.
 * A set of courses that would fill this block (possibly equivalences) is given in
 * `recommend`.
 * Because equivalences could be potentially unknown to the frontend and we don't want
 * to show the user equivalence codes, each course is coupled with its name.
 */
export type CurriculumErr = {
    is_err?: boolean;
    kind?: 'curr';
    associated_to?: null;
    blocks: Array<Array<string>>;
    credits: number;
    fill_options: Array<Array<any>>;
};

