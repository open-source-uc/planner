/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * A diagnostic message, that may be associated to a course that the user is taking.
 */
export type Diagnostic = {
    course_code?: string;
    is_warning: boolean;
    message: string;
};

