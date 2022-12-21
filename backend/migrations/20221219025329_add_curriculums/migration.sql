-- CreateTable
CREATE TABLE "CurriculumBlock" (
    "id" TEXT NOT NULL,
    "kind" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "req" JSONB NOT NULL,

    CONSTRAINT "CurriculumBlock_pkey" PRIMARY KEY ("id")
);
