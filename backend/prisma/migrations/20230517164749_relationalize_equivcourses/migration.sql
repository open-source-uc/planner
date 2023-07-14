/*
  Warnings:

  - You are about to drop the column `courses` on the `Equivalence` table. All the data in the column will be lost.

*/
-- DropIndex
DROP INDEX "Curriculum_cyear_major_minor_title_key";

-- DropIndex
DROP INDEX "Major_cyear_code_key";

-- DropIndex
DROP INDEX "MajorMinor_cyear_major_minor_key";

-- DropIndex
DROP INDEX "Minor_cyear_code_key";

-- DropIndex
DROP INDEX "Title_cyear_code_key";

-- AlterTable
ALTER TABLE "Curriculum" ADD CONSTRAINT "Curriculum_pkey" PRIMARY KEY ("cyear", "major", "minor", "title");

-- AlterTable
ALTER TABLE "Equivalence" DROP COLUMN "courses";

-- AlterTable
ALTER TABLE "Major" ADD CONSTRAINT "Major_pkey" PRIMARY KEY ("cyear", "code");

-- AlterTable
ALTER TABLE "MajorMinor" ADD CONSTRAINT "MajorMinor_pkey" PRIMARY KEY ("cyear", "major", "minor");

-- AlterTable
ALTER TABLE "Minor" ADD CONSTRAINT "Minor_pkey" PRIMARY KEY ("cyear", "code");

-- AlterTable
ALTER TABLE "Title" ADD CONSTRAINT "Title_pkey" PRIMARY KEY ("cyear", "code");

-- CreateTable
CREATE TABLE "EquivalenceCourse" (
    "equiv_code" TEXT NOT NULL,
    "course_code" TEXT NOT NULL,

    CONSTRAINT "EquivalenceCourse_pkey" PRIMARY KEY ("equiv_code","course_code")
);

-- AddForeignKey
ALTER TABLE "EquivalenceCourse" ADD CONSTRAINT "EquivalenceCourse_course_code_fkey" FOREIGN KEY ("course_code") REFERENCES "Course"("code") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "EquivalenceCourse" ADD CONSTRAINT "EquivalenceCourse_equiv_code_fkey" FOREIGN KEY ("equiv_code") REFERENCES "Equivalence"("code") ON DELETE RESTRICT ON UPDATE CASCADE;
