/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ValidatablePlan } from './ValidatablePlan';

/**
 * Detailed, typed view of a plan in the database.
 * The only difference between this type and `DbPlan` (ie. the plan schema) is that
 * the type of `PlanView.validatable_plan` is `ValidatablePlan`, while the type of
 * `Plan.validatable_plan` is `Json`.
 */
export type PlanView = {
    id: string;
    created_at: string;
    updated_at: string;
    name: string;
    is_favorite: boolean;
    /**
     * A RUT, like 12345678-K. No dots, no leading zeroes, uppercase K.
     */
    user_rut: string;
    validatable_plan: ValidatablePlan;
};

