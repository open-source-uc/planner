/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Course } from '../models/Course';
import type { CourseOverview } from '../models/CourseOverview';
import type { FlatValidationResult } from '../models/FlatValidationResult';
import type { LowDetailPlanView } from '../models/LowDetailPlanView';
import type { PlanView } from '../models/PlanView';
import type { ValidatablePlan } from '../models/ValidatablePlan';

import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export class DefaultService {

    /**
     * Root
     * @returns any Successful Response
     * @throws ApiError
     */
    public static root(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/',
        });
    }

    /**
     * Health
     * @returns any Successful Response
     * @throws ApiError
     */
    public static health(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health',
        });
    }

    /**
     * Authenticate
     * Redirect the browser to this page to initiate authentication.
     * @param next
     * @param ticket
     * @returns any Successful Response
     * @throws ApiError
     */
    public static authenticate(
        next?: string,
        ticket?: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/auth/login',
            query: {
                'next': next,
                'ticket': ticket,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Check Auth
     * Request succeeds if authentication was successful.
     * Otherwise, the request fails with 401 Unauthorized.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static checkAuth(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/auth/check',
        });
    }

    /**
     * Sync Courses
     * Initiate a synchronization of the internal database from external sources.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static syncCourses(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/sync',
        });
    }

    /**
     * Search Courses
     * Fetches a list of courses that match a given search query string.
     * @param text
     * @returns CourseOverview Successful Response
     * @throws ApiError
     */
    public static searchCourses(
        text: string,
    ): CancelablePromise<Array<CourseOverview>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/courses/search',
            query: {
                'text': text,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Course Details
     * For a list of course codes, fetch a corresponding list of course details.
     *
     * Request example: `/api/courses?codes=IIC2233&codes=IIC2173`
     * @param codes
     * @returns Course Successful Response
     * @throws ApiError
     */
    public static getCourseDetails(
        codes: Array<string>,
    ): CancelablePromise<Array<Course>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/courses',
            query: {
                'codes': codes,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Rebuild Validation Rules
     * Recache course information from internal database.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static rebuildValidationRules(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/plan/rebuild',
        });
    }

    /**
     * Validate Plan
     * Validate a plan, generating diagnostics.
     * @param requestBody
     * @returns FlatValidationResult Successful Response
     * @throws ApiError
     */
    public static validatePlan(
        requestBody: ValidatablePlan,
    ): CancelablePromise<FlatValidationResult> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/plan/validate',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Generate Plan
     * Generate a hopefully error-free plan from an initial plan.
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static generatePlan(
        requestBody: ValidatablePlan,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/plan/generate',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Read Plans
     * Fetches an overview of all the plans in the storage of the current user.
     * Fails if the user is not logged in.
     * Does not return the courses in each plan, only the plan metadata required
     * to show the users their list of plans (e.g. the plan id).
     * @returns LowDetailPlanView Successful Response
     * @throws ApiError
     */
    public static readPlans(): CancelablePromise<Array<LowDetailPlanView>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/plan/storage',
        });
    }

    /**
     * Update Plan
     * Modifies the courses of a plan by id.
     * Requires the current user to be the owner of this plan.
     * Returns the updated plan.
     * @param planId
     * @param requestBody
     * @returns PlanView Successful Response
     * @throws ApiError
     */
    public static updatePlan(
        planId: string,
        requestBody: ValidatablePlan,
    ): CancelablePromise<PlanView> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/plan/storage',
            query: {
                'plan_id': planId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Save Plan
     * Save a plan with the given name in the storage of the current user.
     * Fails if the user is not logged  in.
     * @param name
     * @param requestBody
     * @returns PlanView Successful Response
     * @throws ApiError
     */
    public static savePlan(
        name: string,
        requestBody: ValidatablePlan,
    ): CancelablePromise<PlanView> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/plan/storage',
            query: {
                'name': name,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Delete Plan
     * Deletes a plan by ID.
     * Requires the current user to be the owner of this plan.
     * Returns the removed plan.
     * @param planId
     * @returns PlanView Successful Response
     * @throws ApiError
     */
    public static deletePlan(
        planId: string,
    ): CancelablePromise<PlanView> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/plan/storage',
            query: {
                'plan_id': planId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Read Plan
     * Fetch the plan details for a given plan id.
     * Requires the current user to be the plan owner.
     * @param planId
     * @returns PlanView Successful Response
     * @throws ApiError
     */
    public static readPlan(
        planId: string,
    ): CancelablePromise<PlanView> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/plan/storage/details',
            query: {
                'plan_id': planId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Update Plan Metadata
     * Modifies the metadata of a plan (currently only `name` or `is_favorite`).
     * Modify one attribute per request.
     * Requires the current user to be the owner of this plan.
     * Returns the updated plan.
     * @param planId
     * @param setName
     * @param setFavorite
     * @returns PlanView Successful Response
     * @throws ApiError
     */
    public static updatePlanMetadata(
        planId: string,
        setName?: string,
        setFavorite?: boolean,
    ): CancelablePromise<PlanView> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/plan/storage/metadata',
            query: {
                'plan_id': planId,
                'set_name': setName,
                'set_favorite': setFavorite,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

}
