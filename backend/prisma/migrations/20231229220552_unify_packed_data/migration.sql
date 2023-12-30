/*
  Warnings:

  - You are about to drop the `CachedCourseInfo` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `CachedCurriculum` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropTable
DROP TABLE "CachedCourseInfo";

-- DropTable
DROP TABLE "CachedCurriculum";

-- CreateTable
CREATE TABLE "PackedData" (
    "id" TEXT NOT NULL,
    "data" TEXT NOT NULL,

    CONSTRAINT "PackedData_pkey" PRIMARY KEY ("id")
);
