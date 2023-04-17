/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { ConcreteId } from './ConcreteId';
import type { EquivalenceId } from './EquivalenceId';
import type { StudentInfo } from './StudentInfo';

export type StudentContext = {
    info: StudentInfo;
    passed_courses: Array<Array<(ConcreteId | EquivalenceId)>>;
};

