/*
  Warnings:

  - Added the required column `is_unessential` to the `Equivalence` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
DELETE FROM "EquivalenceCourse";
DELETE FROM "Equivalence";
ALTER TABLE "Equivalence" ADD COLUMN     "is_unessential" BOOLEAN NOT NULL;
