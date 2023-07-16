/*
  Warnings:

  - Added the required column `index` to the `EquivalenceCourse` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "EquivalenceCourse" ADD COLUMN     "index" INTEGER NOT NULL;
