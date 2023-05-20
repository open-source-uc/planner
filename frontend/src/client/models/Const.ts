/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * A constant, fixed value of True or False.
 */
export type Const = {
    hash?: Blob;
    expr?: Const.expr;
    value: boolean;
};

export namespace Const {

    export enum expr {
        CONST = 'const',
    }


}

