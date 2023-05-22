-- CreateTable
CREATE TABLE "CachedCourseInfo" (
    "id" TEXT NOT NULL,
    "info" JSONB NOT NULL,

    CONSTRAINT "CachedCourseInfo_pkey" PRIMARY KEY ("id")
);
