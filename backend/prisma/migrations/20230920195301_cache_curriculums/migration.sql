/*
  Warnings:

  - You are about to drop the `Curriculum` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropTable
DROP TABLE "Curriculum";

-- CreateTable
CREATE TABLE "CachedCurriculum" (
    "id" TEXT NOT NULL,
    "curriculums" TEXT NOT NULL,

    CONSTRAINT "CachedCurriculum_pkey" PRIMARY KEY ("id")
);
