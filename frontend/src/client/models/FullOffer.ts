/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { Major } from './Major';
import type { Minor } from './Minor';
import type { Title } from './Title';

export type FullOffer = {
    majors: Array<Major>;
    minors: Array<Minor>;
    titles: Array<Title>;
};

