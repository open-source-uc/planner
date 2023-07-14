-- CreateTable
CREATE TABLE "Curriculum" (
    "cyear" TEXT NOT NULL,
    "major" TEXT NOT NULL,
    "minor" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "curriculum" JSONB NOT NULL
);

-- CreateTable
CREATE TABLE "PlanRecommendation" (
    "cyear" TEXT NOT NULL,
    "major" TEXT NOT NULL,
    "minor" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "recommended_plan" JSONB NOT NULL
);

-- CreateIndex
CREATE UNIQUE INDEX "Curriculum_cyear_major_minor_title_key" ON "Curriculum"("cyear", "major", "minor", "title");

-- CreateIndex
CREATE UNIQUE INDEX "PlanRecommendation_cyear_major_minor_title_key" ON "PlanRecommendation"("cyear", "major", "minor", "title");
