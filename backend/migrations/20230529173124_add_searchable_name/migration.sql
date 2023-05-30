/*
  Warnings:

  - Added the required column `searchable_name` to the `Course` table without a default value. This is not possible if the table is not empty.

*/

-- Clear course cache so that it is redownloaded from the new source.
DELETE FROM "EquivalenceCourse";
DELETE FROM "Equivalence";
DELETE FROM "Course";
DELETE FROM "CachedCourseInfo" WHERE id = 'cached-course-info';

-- AlterTable
ALTER TABLE "Course" ADD COLUMN     "searchable_name" TEXT NOT NULL;
