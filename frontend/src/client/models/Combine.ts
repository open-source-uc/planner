/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

export type Combine = {
    name: string;
    cap?: number;
    exclusive?: boolean;
    children: Array<(Combine | string)>;
};

