/*
  Warnings:

  - Added the required column `cyear` to the `MajorMinor` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "MajorMinor" ADD COLUMN     "cyear" TEXT NOT NULL;
