-- CreateTable
CREATE TABLE "Course" (
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "credits" INTEGER NOT NULL,
    "deps" JSONB NOT NULL,
    "program" TEXT NOT NULL,
    "school" TEXT NOT NULL,
    "area" TEXT,
    "category" TEXT,

    CONSTRAINT "Course_pkey" PRIMARY KEY ("code")
);
