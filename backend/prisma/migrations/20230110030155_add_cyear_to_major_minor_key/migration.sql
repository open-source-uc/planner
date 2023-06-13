/*
  Warnings:

  - A unique constraint covering the columns `[cyear,major,minor]` on the table `MajorMinor` will be added. If there are existing duplicate values, this will fail.

*/
-- DropIndex
DROP INDEX "MajorMinor_major_minor_key";

-- CreateIndex
CREATE UNIQUE INDEX "MajorMinor_cyear_major_minor_key" ON "MajorMinor"("cyear", "major", "minor");
