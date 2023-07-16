/*
  Warnings:

  - Added the required column `is_available` to the `Course` table without a default value. This is not possible if the table is not empty.
  - Added the required column `is_relevant` to the `Course` table without a default value. This is not possible if the table is not empty.
  - Added the required column `semestrality_first` to the `Course` table without a default value. This is not possible if the table is not empty.
  - Added the required column `semestrality_second` to the `Course` table without a default value. This is not possible if the table is not empty.
  - Added the required column `semestrality_tav` to the `Course` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "Course" ADD COLUMN     "is_available" BOOLEAN NOT NULL,
ADD COLUMN     "is_relevant" BOOLEAN NOT NULL,
ADD COLUMN     "semestrality_first" BOOLEAN NOT NULL,
ADD COLUMN     "semestrality_second" BOOLEAN NOT NULL,
ADD COLUMN     "semestrality_tav" BOOLEAN NOT NULL;
