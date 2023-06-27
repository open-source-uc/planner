-- AlterTable
ALTER TABLE "Course" ADD COLUMN     "banner_inv_equivs" TEXT[];
DELETE FROM "EquivalenceCourse";
DELETE FROM "Equivalence";
DELETE FROM "Course";
DELETE FROM "CachedCourseInfo";
