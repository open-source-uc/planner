/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AccessLevelOverview } from '../models/AccessLevelOverview';
import type { Body_generate_plan } from '../models/Body_generate_plan';
import type { CourseDetails } from '../models/CourseDetails';
import type { CourseFilter } from '../models/CourseFilter';
import type { CourseOverview } from '../models/CourseOverview';
import type { EquivDetails } from '../models/EquivDetails';
import type { FullOffer } from '../models/FullOffer';
import type { HealthResponse } from '../models/HealthResponse';
import type { LowDetailPlanView } from '../models/LowDetailPlanView';
import type { Major } from '../models/Major';
import type { Minor } from '../models/Minor';
import type { PlanView } from '../models/PlanView';
import type { StudentContext } from '../models/StudentContext';
import type { Title } from '../models/Title';
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
     * @returns HealthResponse Successful Response
     * @throws ApiError
     */
    public static health(): CancelablePromise<HealthResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health',
        });
    }

    /**
     * Sync Database
     * Initiate a synchronization of the internal database from external sources.
     *
     * NOTE: This endpoint is currently broken: a server restart is necessary after syncing
     * the database in order for the changes to reach all workers.
     * @param courses
     * @param curriculums
     * @param offer
     * @param packedcourses
     * @returns any Successful Response
     * @throws ApiError
     */
    public static syncDatabase(
        courses: boolean,
        curriculums: boolean,
        offer: boolean,
        packedcourses: boolean,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/admin/sync',
            query: {
                'courses': courses,
                'curriculums': curriculums,
                'offer': offer,
                'packedcourses': packedcourses,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * View Mods
     * Show a list of all current mods with username and RUT. Up to 50 records.
     * @returns AccessLevelOverview Successful Response
     * @throws ApiError
     */
    public static viewMods(): CancelablePromise<Array<AccessLevelOverview>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/admin/mod',
        });
    }

    /**
     * Add Mod
     * Give mod access to a user with the specified RUT.
     * @param rut
     * @returns any Successful Response
     * @throws ApiError
     */
    public static addMod(
        rut: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/admin/mod',
            query: {
                'rut': rut,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Remove Mod
     * Remove mod access from a user with the specified RUT.
     * @param rut
     * @returns any Successful Response
     * @throws ApiError
     */
    public static removeMod(
        rut: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/admin/mod',
            query: {
                'rut': rut,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Search Course Details
     * Fetches a list of courses that match the given name (or code),
     * credits and school.
     * @param requestBody
     * @returns CourseOverview Successful Response
     * @throws ApiError
     */
    public static searchCourseDetails(
        requestBody: CourseFilter,
    ): CancelablePromise<Array<CourseOverview>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/course/search/details',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Search Course Codes
     * Fetches a list of courses that match the given name (or code),
     * credits and school.
     * Returns only the course codes, but allows up to 3000 results.
     * @param requestBody
     * @returns string Successful Response
     * @throws ApiError
     */
    public static searchCourseCodes(
        requestBody: CourseFilter,
    ): CancelablePromise<Array<string>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/course/search/codes',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Pseudocourse Details
     * For a list of course or equivalence codes, fetch a corresponding list of
     * course/equivalence details.
     * Returns null in the corresponding slot if the code is unknown.
     *
     * Request example: `/api/courses?codes=IIC2233&codes=IIC2173`
     * @param codes
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getPseudocourseDetails(
        codes: Array<string>,
    ): CancelablePromise<Array<(CourseDetails | EquivDetails)>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/course/details',
            query: {
                'codes': codes,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Majors
     * Get all the available majors for a given curriculum version (cyear).
     * @param cyear
     * @returns Major Successful Response
     * @throws ApiError
     */
    public static getMajors(
        cyear: string,
    ): CancelablePromise<Array<Major>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/offer/major',
            query: {
                'cyear': cyear,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Minors
     * @param cyear
     * @param majorCode
     * @returns Minor Successful Response
     * @throws ApiError
     */
    public static getMinors(
        cyear: string,
        majorCode?: string,
    ): CancelablePromise<Array<Minor>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/offer/minor',
            query: {
                'cyear': cyear,
                'major_code': majorCode,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Titles
     * @param cyear
     * @returns Title Successful Response
     * @throws ApiError
     */
    public static getTitles(
        cyear: string,
    ): CancelablePromise<Array<Title>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/offer/title',
            query: {
                'cyear': cyear,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Offer
     * @param cyear
     * @param majorCode
     * @returns FullOffer Successful Response
     * @throws ApiError
     */
    public static getOffer(
        cyear: string,
        majorCode?: string,
    ): CancelablePromise<FullOffer> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/offer/',
            query: {
                'cyear': cyear,
                'major_code': majorCode,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Empty Plan For User
     * Generate an empty plan using the current user as context.
     * For example, the created plan includes all passed courses, uses the curriculum
     * version for the given user and selects the student's official choice of
     * major/minor/title if available.
     *
     * (Currently this is equivalent to `empty_guest_plan()` until we get user data)
     * @returns ValidatablePlan Successful Response
     * @throws ApiError
     */
    public static emptyPlanForUser(): CancelablePromise<ValidatablePlan> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/plan/empty_for',
        });
    }

    /**
     * Empty Plan For Any User
     * Same functionality as `empty_plan_for_user`, but works for any user identified by
     * their RUT with `user_rut`.
     * Moderator access is required.
     * @param userRut
     * @returns ValidatablePlan Successful Response
     * @throws ApiError
     */
    public static emptyPlanForAnyUser(
        userRut: string,
    ): CancelablePromise<ValidatablePlan> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/plan/empty_for_any',
            query: {
                'user_rut': userRut,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Empty Guest Plan
     * Generates a generic empty plan with no user context, using the latest curriculum
     * version.
     * @returns ValidatablePlan Successful Response
     * @throws ApiError
     */
    public static emptyGuestPlan(): CancelablePromise<ValidatablePlan> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/plan/empty_guest',
        });
    }

    /**
     * Validate Guest Plan
     * Validate a plan, generating diagnostics.
     * @param requestBody
     * @returns ValidationResult Successful Response
     * @throws ApiError
     */
    public static validateGuestPlan(
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
     * Validate Plan For User
     * Validate a plan, generating diagnostics.
     * Includes diagnostics tailored for the given user and skips diagnostics that do not
     * apply to the particular student.
     * @param requestBody
     * @returns ValidationResult Successful Response
     * @throws ApiError
     */
    public static validatePlanForUser(
        requestBody: ValidatablePlan,
    ): CancelablePromise<ValidationResult> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/plan/validate_for',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Validate Plan For Any User
     * Same functionality as `validate_plan_for_user`, but works for any user identified by
     * their RUT with `user_rut`.
     * Moderator access is required.
     * @param userRut
     * @param requestBody
     * @returns ValidationResult Successful Response
     * @throws ApiError
     */
    public static validatePlanForAnyUser(
        userRut: string,
        requestBody: ValidatablePlan,
    ): CancelablePromise<ValidationResult> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/plan/validate_for_any',
            query: {
                'user_rut': userRut,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Curriculum Validation Graph
     * Get the curriculum validation graph for a certain plan, in Graphviz DOT format.
     * Useful for debugging and kind of a bonus easter egg.
     * @param mode
     * @param requestBody
     * @returns string Successful Response
     * @throws ApiError
     */
    public static getCurriculumValidationGraph(
        mode: string,
        requestBody: ValidatablePlan,
    ): CancelablePromise<string> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/plan/curriculum_graph',
            query: {
                'mode': mode,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Generate Plan
     * From a base plan, generate a new plan that should lead the user to earn their title
     * of choice.
     * @param requestBody
     * @returns ValidatablePlan Successful Response
     * @throws ApiError
     */
    public static generatePlan(
        requestBody: Body_generate_plan,
    ): CancelablePromise<ValidatablePlan> {
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
     * Fails if the user is not logged in.
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
     * Read Any Plans
     * Same functionality as `read_plans`, but works for any user identified by
     * their RUT with `user_rut`.
     * Moderator access is required.
     * @param userRut
     * @returns LowDetailPlanView Successful Response
     * @throws ApiError
     */
    public static readAnyPlans(
        userRut: string,
    ): CancelablePromise<Array<LowDetailPlanView>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/plan/storage/any',
            query: {
                'user_rut': userRut,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Update Any Plan
     * Same functionality as `update_plan`, but works for any plan of any user
     * identified by their RUT.
     * Moderator access is required.
     * @param planId
     * @param requestBody
     * @returns PlanView Successful Response
     * @throws ApiError
     */
    public static updateAnyPlan(
        planId: string,
        requestBody: ValidatablePlan,
    ): CancelablePromise<PlanView> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/plan/storage/any',
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
     * Save Any Plan
     * Same functionality as `save_plan`, but works for any user identified by
     * their RUT with `user_rut`.
     * Moderator access is required.
     * All `/storage/any` endpoints (and sub-resources) should require
     * moderator access.
     * @param name
     * @param userRut
     * @param requestBody
     * @returns PlanView Successful Response
     * @throws ApiError
     */
    public static saveAnyPlan(
        name: string,
        userRut: string,
        requestBody: ValidatablePlan,
    ): CancelablePromise<PlanView> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/plan/storage/any',
            query: {
                'name': name,
                'user_rut': userRut,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Delete Any Plan
     * Same functionality as `delete_plan`, but works for any plan of any user
     * identified by their RUT.
     * Moderator access is required.
     * @param planId
     * @returns PlanView Successful Response
     * @throws ApiError
     */
    public static deleteAnyPlan(
        planId: string,
    ): CancelablePromise<PlanView> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/plan/storage/any',
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
     * Read Any Plan
     * Same functionality as `read_plan`, but works for any plan of any user
     * identified by their RUT.
     * Moderator access is required.
     * @param planId
     * @returns PlanView Successful Response
     * @throws ApiError
     */
    public static readAnyPlan(
        planId: string,
    ): CancelablePromise<PlanView> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/plan/storage/any/details',
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

    /**
     * Update Any Plan Metadata
     * Same functionality as `update_plan_metadata`, but works for any plan of any user
     * identified by their RUT.
     * Moderator access is required.
     * @param planId
     * @param setName
     * @param setFavorite
     * @returns PlanView Successful Response
     * @throws ApiError
     */
    public static updateAnyPlanMetadata(
        planId: string,
        setName?: string,
        setFavorite?: boolean,
    ): CancelablePromise<PlanView> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/plan/storage/any/metadata',
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

    /**
     * Authenticate
     * Redirect the browser to this page to initiate authentication.
     * @param next
     * @param ticket
     * @param impersonateRut
     * @returns any Successful Response
     * @throws ApiError
     */
    public static authenticate(
        next?: string,
        ticket?: string,
        impersonateRut?: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/user/login',
            query: {
                'next': next,
                'ticket': ticket,
                'impersonate_rut': impersonateRut,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Check Auth
     * Request succeeds if user authentication was successful.
     * Otherwise, the request fails with 401 Unauthorized.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static checkAuth(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/user/check',
        });
    }

    /**
     * Check Mod
     * Request succeeds if user authentication and mod authorization were successful.
     * Otherwise, the request fails with 401 Unauthorized or 403 Forbidden.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static checkMod(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/user/check/mod',
        });
    }

    /**
     * Check Admin
     * Request succeeds if user authentication and admin authorization were successful.
     * Otherwise, the request fails with 401 Unauthorized or 403 Forbidden.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static checkAdmin(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/user/check/admin',
        });
    }

    /**
     * Get Student Info
     * Get the student info for the currently logged in user.
     * Requires authentication (!)
     * This forwards a request to the SIDING service.
     * @returns StudentContext Successful Response
     * @throws ApiError
     */
    public static getStudentInfo(): CancelablePromise<StudentContext> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/user/info',
        });
    }

}
