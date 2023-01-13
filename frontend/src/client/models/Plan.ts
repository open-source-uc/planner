/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Represents a Plan record
 */
export type Plan = {
    id: string;
    created_at: string;
    updated_at: string;
    name: string;
    user_rut: string;
    validatable_plan?: string;
};

