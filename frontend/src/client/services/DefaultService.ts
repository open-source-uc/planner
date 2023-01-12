/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ValidatablePlan } from '../models/ValidatablePlan';
import type { ValidationResult } from '../models/ValidationResult';

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
     * @returns any Successful Response
     * @throws ApiError
     */
    public static syncCourses(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/courses/sync',
        });
    }

    /**
     * Search Courses
     * @param text
     * @returns any Successful Response
     * @throws ApiError
     */
    public static searchCourses(
        text: string,
    ): CancelablePromise<any> {
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
     * request example: API/courses?codes=IIC2233&codes=IIC2173
     * @param codes
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCourseDetails(
        codes: Array<string>,
    ): CancelablePromise<any> {
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
     * @param requestBody
     * @returns ValidationResult Successful Response
     * @throws ApiError
     */
    public static validatePlan(
        requestBody: ValidatablePlan,
    ): CancelablePromise<ValidationResult> {
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
     * @returns any Successful Response
     * @throws ApiError
     */
    public static readPlans(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/plan/storage',
        });
    }

    /**
     * Update Plan
     * @param planId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updatePlan(
        planId: string,
        requestBody: ValidatablePlan,
    ): CancelablePromise<any> {
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
     * @param name
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static savePlan(
        name: string,
        requestBody: ValidatablePlan,
    ): CancelablePromise<any> {
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
     * @param planId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deletePlan(
        planId: string,
    ): CancelablePromise<any> {
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
     * @param planId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static readPlan(
        planId: string,
    ): CancelablePromise<any> {
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
     * Rename Plan
     * @param planId
     * @param newName
     * @returns any Successful Response
     * @throws ApiError
     */
    public static renamePlan(
        planId: string,
        newName: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/plan/storage/name',
            query: {
                'plan_id': planId,
                'new_name': newName,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

}
