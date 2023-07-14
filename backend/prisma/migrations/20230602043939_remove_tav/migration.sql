/*
  Warnings:

  - You are about to drop the column `semestrality_tav` on the `Course` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "Course" DROP COLUMN "semestrality_tav";
DELETE FROM "CachedCourseInfo" WHERE id = 'cached-course-info';
