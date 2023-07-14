/*
  Warnings:

  - Added the required column `canonical_equiv` to the `Course` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
DELETE FROM "EquivalenceCourse";
DELETE FROM "Equivalence";
DELETE FROM "Course";
ALTER TABLE "Course" ADD COLUMN     "banner_equivs" TEXT[],
ADD COLUMN     "canonical_equiv" TEXT NOT NULL;
DELETE FROM "CachedCourseInfo";
